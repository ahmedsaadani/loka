# Loka — raccourcis de développement.
# Sous Windows sans `make`, utiliser : powershell -File scripts/dev.ps1 <cible>
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help dev down logs ps build api-shell web-shell migrate makemigrations seed seed-reset \
        lint lint-api lint-web test test-api test-web e2e audit types clean \n        backup backups restore

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

dev: ## Démarre toute la stack (postgres, redis, minio, api, worker, web)
	$(COMPOSE) up -d --build
	@echo "web  : http://localhost:3000"
	@echo "api  : http://localhost:18000/api/v1/docs/"
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

seed: ## Charge les données de démo (villes, quartiers, biens avec photos, comptes de test)
	$(COMPOSE) exec api python manage.py seed

seed-reset: ## Supprime et recrée les biens de démo (photos comprises)
	$(COMPOSE) exec api python manage.py seed --reset

types: ## Génère les types TS depuis le schéma OpenAPI de l'API
	$(COMPOSE) exec web npm run api:types

backup: ## Sauvegarde chiffrée immédiate de PostgreSQL vers le bucket privé (+ rotation)
	$(COMPOSE) run --rm -T api python manage.py backup_db

backups: ## Liste les sauvegardes disponibles
	$(COMPOSE) run --rm -T api python manage.py list_backups

restore: ## DESTRUCTIF : restaure la base depuis une sauvegarde. Usage : make restore name=backups/db/...
	@test -n "$(name)" || (echo "usage : make restore name=backups/db/AAAA/MM/loka-....dump.fernet" && exit 1)
	$(COMPOSE) run --rm -T -e ALLOW_DB_RESTORE=1 api python manage.py restore_db "$(name)" --yes

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

e2e: ## Tests Playwright (stack démarrée et seedée)
	$(COMPOSE) exec web npx playwright test

audit: ## bandit + pip-audit + npm audit
	$(COMPOSE) exec api bandit -q -r . -c pyproject.toml
	$(COMPOSE) exec api pip-audit -r requirements/base.txt --strict
	$(COMPOSE) exec web npm audit --omit=dev --audit-level=high
