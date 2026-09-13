# Sauvegardes PostgreSQL

Sauvegardes automatiques, chiffrées, de la base PostgreSQL/PostGIS de Loka. Code : `apps/api/core/backups.py`, commandes `backup_db`, `list_backups`, `restore_db`, tâche Celery `core.tasks.backup_database`.

## Quoi, où, comment

| | |
|---|---|
| **Outils** | `pg_dump`/`pg_restore` **de la même majeure que le serveur** (postgresql-client-16 via le dépôt PGDG dans `infra/docker/api.Dockerfile`). Un client plus récent (17) émet `SET transaction_timeout`, inconnu de PostgreSQL 16, et `pg_restore` sort en erreur. Lors d'une montée de version du serveur, monter le client en même temps. |
| **Contenu** | Dump complet de la base `default` (`pg_dump -Fc`, format custom compressé : schéma + données, extensions PostGIS incluses). |
| **Destination** | Bucket privé S3/MinIO (`S3_BUCKET_PRIVATE`), préfixe `backups/db/AAAA/MM/loka-AAAAMMJJ-HHMMSS.dump.fernet` (heure locale Africa/Tunis). |
| **Chiffrement** | Symétrique, [Fernet](https://cryptography.io/en/latest/fernet/) (AES-128-CBC + HMAC-SHA256) avec la clé `BACKUP_ENCRYPTION_KEY`. Le fichier stocké est illisible sans la clé, même pour qui a accès au bucket. |
| **Planification** | Tâche Celery `core.tasks.backup_database`, tous les jours à 03:00 (`CELERY_BEAT_SCHEDULE`, fuseau `Africa/Tunis`). Nécessite un processus `celery beat` en prod. |
| **Rétention** | Toutes les sauvegardes des 7 derniers jours (`BACKUP_RETENTION_DAYS`) + la plus ancienne sauvegarde de chacune des 4 dernières semaines ISO (`BACKUP_RETENTION_WEEKS`). Le reste est supprimé après chaque sauvegarde réussie. Les fichiers dont le nom ne suit pas le motif ne sont jamais touchés. |
| **Désactivation** | `BACKUP_ENCRYPTION_KEY` vide → `create_backup()` retourne `None` et journalise un avertissement. Aucune sauvegarde en clair n'est jamais écrite. |

Ce qui **n'est pas** sauvegardé par ce mécanisme : les objets des buckets S3 (photos, documents d'identité, contrats). Ils doivent être couverts par le versioning / la réplication du fournisseur de stockage.

## Générer et conserver la clé

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

- Renseigner `BACKUP_ENCRYPTION_KEY=<clé>` dans `.env` (dev) ou dans le gestionnaire de secrets (prod).
- **Conserver une copie de la clé hors du serveur** (coffre-fort d'équipe). Une sauvegarde sans sa clé est définitivement perdue.
- Changer la clé = les anciennes sauvegardes restent chiffrées avec l'ancienne clé : garder l'ancienne clé tant que des sauvegardes l'utilisent (4 semaines).
- Le mot de passe de la base est transmis à `pg_dump`/`pg_restore` via `PGPASSWORD` dans l'environnement du sous-processus, jamais dans une ligne de commande.

## Sauvegarde manuelle

```bash
make backup
# ou
docker compose run --rm -T api python manage.py backup_db
# → backups/db/2026/09/loka-20260913-142536.dump.fernet
#   supprimé : backups/db/2026/08/... (le cas échéant)
```

## Lister les sauvegardes

```bash
make backups
# ou
docker compose run --rm -T api python manage.py list_backups
# 2026-09-13 14:25:36  backups/db/2026/09/loka-20260913-142536.dump.fernet
```

## Restauration — procédure pas à pas

`restore_db` est **destructif** : `pg_restore --clean --if-exists --no-owner` supprime puis recrée chaque objet de la base cible. Deux garde-fous : le flag `--yes` **et**, hors `DEBUG`, la variable `ALLOW_DB_RESTORE=1` dans l'environnement du processus (à passer ponctuellement, jamais dans `.env`).

### 1. Répétition à blanc dans une base de secours (recommandé)

Toujours restaurer d'abord dans une base jetable pour valider la sauvegarde et la clé, sans toucher à la production.

```bash
# a. Repérer la sauvegarde à restaurer
docker compose run --rm -T api python manage.py list_backups

# b. Créer une base vide
docker compose exec -T postgres psql -U loka -c "CREATE DATABASE loka_restore_test"

# c. Restaurer dedans en surchargeant DATABASE_URL
docker compose run --rm -T \
  -e ALLOW_DB_RESTORE=1 \
  -e DATABASE_URL=postgis://loka:loka@postgres:5432/loka_restore_test \
  api python manage.py restore_db backups/db/2026/09/loka-20260913-142536.dump.fernet --yes

# d. Vérifier le contenu
docker compose exec -T postgres psql -U loka -d loka_restore_test -c "SELECT count(*) FROM listings_property"

# e. Supprimer la base de secours
docker compose exec -T postgres psql -U loka -c "DROP DATABASE loka_restore_test"
```

Ce scénario a été joué en dev le 13/09/2026 : dump de la base de dev (`listings_property` = 34 lignes), restauration dans `loka_restore_test`, même comptage obtenu, base supprimée ensuite.

### 2. Restauration réelle

1. **Prévenir** l'équipe, mettre le site en maintenance (arrêter `api`, `worker` et `web` : `docker compose stop api worker web`). Aucune écriture ne doit avoir lieu pendant la restauration.
2. **Faire une sauvegarde de l'état courant** même s'il est cassé (`make backup` ou `pg_dump` manuel) : on veut pouvoir revenir en arrière.
3. Choisir la sauvegarde (`list_backups`) et **la valider en base de secours** (étape 1 ci-dessus).
4. Restaurer dans la base de production :
   ```bash
   docker compose run --rm -T -e ALLOW_DB_RESTORE=1 api python manage.py restore_db <nom> --yes
   # équivalent : make restore name=<nom>
   ```
5. Appliquer les migrations manquantes si le code a avancé depuis la sauvegarde : `docker compose run --rm -T api python manage.py migrate`.
6. Vérifier : `python manage.py check`, quelques comptages (`listings_property`, `bookings_booking`, `accounts_user`), connexion à l'admin.
7. Relancer les services (`docker compose up -d api worker web`) et surveiller les logs.
8. Consigner l'incident (date, sauvegarde utilisée, données perdues entre la sauvegarde et l'incident).

Les objets S3 (photos, documents) ne sont pas dans le dump : après restauration, des lignes peuvent référencer des fichiers créés entre la sauvegarde et l'incident (ils existent encore dans le bucket) ou, inversement, des fichiers orphelins peuvent subsister. C'est sans gravité mais à connaître.

## Checklist de reprise après sinistre

- [ ] `BACKUP_ENCRYPTION_KEY` de prod disponible hors du serveur (coffre-fort d'équipe) et testée.
- [ ] Identifiants d'accès au bucket privé disponibles hors du serveur.
- [ ] `celery beat` tourne en prod et la tâche `backup-database` apparaît dans ses logs à 03:00.
- [ ] Une sauvegarde datée de moins de 24 h existe (`list_backups`), taille cohérente avec la veille.
- [ ] Répétition de restauration à blanc jouée **au moins une fois par mois** (étape 1) et durée notée.
- [ ] Le bucket privé a le versioning ou une réplication activée (protection contre une suppression accidentelle par la rotation ou par un tiers).
- [ ] La procédure de restauration réelle (étape 2) est connue de deux personnes au moins.
- [ ] Le RPO accepté est de 24 h (une sauvegarde par nuit) ; si le besoin métier est plus strict, augmenter la fréquence dans `CELERY_BEAT_SCHEDULE`.

## Tests

`apps/api/core/tests/test_backups.py` : `subprocess.run` est mocké (aucun `pg_dump` réel), le stockage est en mémoire. Vérifient le chiffrement, la rétention (fonction pure `select_backups_to_delete` avec une date injectée, horodatage lu dans le nom du fichier), la désactivation sans clé, les refus de restauration et les commandes.
