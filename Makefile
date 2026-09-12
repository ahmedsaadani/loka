# Loka — raccourcis de développement.
# Sous Windows sans `make`, utiliser : powershell -File scripts/dev.ps1 <cible>
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help dev down logs ps build api-shell web-shell migrate makemigrations seed \
        lint lint-api lint-web test test-api test-web types clean

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

dev: ## Démarre toute la stack (postgres, redis, minio, api, worker, web)
	$(COMPOSE) up -d --build
	@echo "web  : http://localhost:3000"
	@echo "api  : http://localhost:8000/api/v1/docs/"
	@echo "minio: http://localhost:9001 (loka / loka-minio-secret)"

down: ## Arrête la stack (conserve les volumes)
	$(COMPOSE) down

clean: ## Arrête la stack et supprime les volumes (base, MinIO)
	$(COMPOSE) down -v

logs: ## Suit les logs de tous les services
	$(COMPOSE) logs -f --tail=100

ps: ## État des services
	$(COMPOSE) ps

build: ## Build des images de prod (multi-stage)
	docker build -f infra/docker/api.Dockerfile --target prod -t loka-api:local apps/api
	docker build -f infra/docker/web.Dockerfile --target prod -t loka-web:local apps/web

api-shell: ## Shell Django
	$(COMPOSE) exec api python manage.py shell

web-shell: ## Shell dans le conteneur web
	$(COMPOSE) exec web sh

migrate: ## Applique les migrations
	$(COMPOSE) exec api python manage.py migrate

makemigrations: ## Génère les migrations
	$(COMPOSE) exec api python manage.py makemigrations

seed: ## Charge les données de démo (villes, quartiers, biens, comptes de test)
	$(COMPOSE) exec api python manage.py seed

types: ## Génère les types TS depuis le schéma OpenAPI de l'API
	$(COMPOSE) exec web npm run api:types

lint: lint-api lint-web ## Lint complet

lint-api: ## ruff + mypy
	$(COMPOSE) exec api ruff check .
	$(COMPOSE) exec api ruff format --check .
	$(COMPOSE) exec api mypy .

lint-web: ## eslint + prettier + tsc
	$(COMPOSE) exec web npm run lint
	$(COMPOSE) exec web npm run format:check
	$(COMPOSE) exec web npm run typecheck

test: test-api test-web ## Tests complets

test-api: ## pytest
	$(COMPOSE) exec api pytest

test-web: ## vitest
	$(COMPOSE) exec web npm run test -- --run
