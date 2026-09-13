<#
.SYNOPSIS
  Équivalent PowerShell du Makefile pour Windows sans `make`.
.EXAMPLE
  powershell -File scripts/dev.ps1 dev
  powershell -File scripts/dev.ps1 test-api
  powershell -File scripts/dev.ps1 restore -Name backups/db/2026/09/loka-20260913-030000.dump.fernet
#>
param(
  [Parameter(Position = 0)]
  [string]$Target = "help",
  # Nom de la sauvegarde pour la cible `restore` (ex. backups/db/2026/09/loka-....dump.fernet)
  [string]$Name = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Compose { docker compose @args; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }

switch ($Target) {
  "help" {
    Write-Host "Cibles : dev, down, clean, logs, ps, build, api-shell, web-shell, migrate, makemigrations, seed, types, lint, lint-api, lint-web, test, test-api, test-web, e2e, audit, backup, backups, restore -Name <nom>"
  }
  "dev" {
    Compose up -d --build
    Write-Host "web  : http://localhost:3000"
    Write-Host "api  : http://localhost:18000/api/v1/docs/"
    Write-Host "minio: http://localhost:9001 (loka / loka-minio-secret)"
  }
  "down"  { Compose down }
  "clean" { Compose down -v }
  "logs"  { Compose logs -f --tail=100 }
  "ps"    { Compose ps }
  "build" {
    docker build -f infra/docker/api.Dockerfile --target prod -t loka-api:local apps/api
    docker build -f infra/docker/web.Dockerfile --target prod -t loka-web:local apps/web
  }
  "api-shell"      { Compose exec api python manage.py shell }
  "web-shell"      { Compose exec web sh }
  "migrate"        { Compose exec api python manage.py migrate }
  "makemigrations" { Compose exec api python manage.py makemigrations }
  "seed"           { Compose exec api python manage.py seed }
  "types"          { Compose exec web npm run api:types }
  "backup"         { Compose run --rm -T api python manage.py backup_db }
  "backups"        { Compose run --rm -T api python manage.py list_backups }
  "restore" {
    # DESTRUCTIF : remplace la base courante. Voir docs/backups.md.
    if (-not $Name) { Write-Error "usage : scripts/dev.ps1 restore -Name backups/db/AAAA/MM/loka-....dump.fernet"; exit 1 }
    Compose run --rm -T -e ALLOW_DB_RESTORE=1 api python manage.py restore_db $Name --yes
  }
  "lint-api" {
    Compose exec api ruff check .
    Compose exec api ruff format --check .
    Compose exec api mypy .
  }
  "lint-web" {
    Compose exec web npm run lint
    Compose exec web npm run format:check
    Compose exec web npm run typecheck
  }
  "lint" { & $PSCommandPath lint-api; & $PSCommandPath lint-web }
  "test-api" { Compose exec api pytest }
  "test-web" { Compose exec web npm run test -- --run }
  "test" { & $PSCommandPath test-api; & $PSCommandPath test-web }
  "e2e" { Compose exec web npx playwright test }
  "audit" {
    Compose exec api bandit -q -r . -c pyproject.toml
    Compose exec api pip-audit -r requirements/base.txt --strict
    Compose exec web npm audit --omit=dev --audit-level=high
  }
  default { Write-Error "Cible inconnue : $Target"; exit 1 }
}
