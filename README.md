# Loka

Plateforme de location d'hébergements en Tunisie. Chaque bien est **visité, photographié et validé par l'équipe Loka** avant publication : aucune annonce non vérifiée.

- Biens : studios, S+1 à S+3, villas, chambres en colocation.
- Durées : nuitée, mensuel (1 à 11 mois), annuel. Un bien peut cumuler les trois modes.
- Marché : Tunisie uniquement. Devise TND, affichage EUR indicatif.
- Langue : FR au MVP, i18n prête pour AR et EN.

## Stack

| Couche | Choix |
|---|---|
| Web | Next.js 15 (App Router, RSC, TypeScript), Tailwind CSS, shadcn/ui |
| API | Django 5 + DRF, Python 3.12, OpenAPI via drf-spectacular |
| Base | PostgreSQL 16 + PostGIS |
| Cache / files | Redis, Celery |
| Stockage | S3 compatible (MinIO en dev), buckets `public` et `private` |
| Auth | JWT, refresh token en cookie httpOnly |
| Cartes | MapLibre GL + OpenStreetMap |
| Conteneurs | Docker + docker compose, Dockerfiles multi-stage |
| CI | GitLab CI |

Détails : [docs/architecture.md](docs/architecture.md), [docs/data-model.md](docs/data-model.md), décisions dans [docs/decisions/](docs/decisions/).

## Prérequis

- Docker Desktop (Compose v2)
- `make` (Git Bash / WSL / `choco install make`). Sans `make` : `powershell -File scripts/dev.ps1 <cible>`
- Node 22 et Python 3.12 en local uniquement pour l'autocomplétion de l'IDE ; tout tourne dans Docker.

## Démarrage

```bash
cp .env.example .env
make dev        # build + démarrage de la stack
make seed       # villes, quartiers, 25 biens de démo, comptes de test
```

| Service | URL |
|---|---|
| Site web | http://localhost:3000 |
| API (docs Swagger) | http://localhost:18000/api/v1/docs/ |
| Schéma OpenAPI | http://localhost:18000/api/v1/schema/ |
| Admin Django | http://localhost:18000/admin/ |
| Console MinIO | http://localhost:9001 (`loka` / `loka-minio-secret`) |
| PostgreSQL (outils locaux) | `localhost:15432`, base `loka`, `loka` / `loka` |
| Redis (outils locaux) | `localhost:16379` |

Les ports 15432 et 16379 évitent les conflits avec un PostgreSQL ou un Redis déjà installés sur la machine.

### Comptes de test (après `make seed`)

| Rôle | Email | Mot de passe |
|---|---|---|
| Admin | admin@loka.tn | loka-admin |
| Staff | staff@loka.tn | loka-staff |
| Hôte | host@loka.tn | loka-host |
| Voyageur | traveler@loka.tn | loka-traveler |

## Commandes

| Commande | Rôle |
|---|---|
| `make dev` / `make down` / `make clean` | Démarrer, arrêter, arrêter et purger les volumes |
| `make logs` | Logs de tous les services |
| `make migrate` / `make makemigrations` | Migrations Django |
| `make seed` | Données de démo |
| `make types` | Régénère les types TS depuis le schéma OpenAPI |
| `make lint` | ruff, mypy, eslint, prettier, tsc |
| `make test` | pytest + vitest |
| `make audit` | bandit, pip-audit, npm audit |
| `make build` | Images de prod |

Tous les tests de l'API tournent avec `config.settings.test` (stockage en mémoire, Celery en mode eager, emails en mémoire) contre la base PostGIS du conteneur.

## Arborescence

```
apps/api      Django : une app par domaine (accounts, geo, listings, availability, bookings, leads, notifications)
apps/web      Next.js : app/(public|auth|account|host|admin), components, lib
infra/        Dockerfiles, nginx, k8s (plus tard)
docs/         architecture, modèle de données, API, SEO, ADR
```

## Conventions

- Code en anglais, UI et contenus en français.
- Commits conventionnels : `feat:`, `fix:`, `chore:`, `docs:`. Une PR par phase.
- Logique métier dans `services.py`, jamais dans les vues ou serializers.
- Statuts (`Property`, `BookingRequest`, `Booking`) changés uniquement via les services de transition.
- Données sensibles (adresse exacte, documents d'identité, contrats) : bucket `private`, URLs signées de 5 min, accès loggé. Jamais dans une réponse publique.
- Images jamais servies en original : variantes WebP `thumb`, `card`, `gallery`, `og` générées par Celery.

## Avancement

Voir [CHANGELOG.md](CHANGELOG.md).
