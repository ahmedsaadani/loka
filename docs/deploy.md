# Déploiement en production

Loka se déploie sur **un seul VPS** avec Docker Compose : nginx (TLS Let's Encrypt), le front Next.js, l'API Django (gunicorn), un worker et un beat Celery, PostgreSQL/PostGIS, Redis, et au choix MinIO auto-hébergé ou un S3 externe. Tout ce qui est décrit ici vit dans [`infra/deploy/`](../infra/deploy/).

| Fichier | Rôle |
|---|---|
| `docker-compose.prod.yml` | Stack de prod (seul nginx publie 80/443, logs json-file 5 × 10 Mo, `restart: unless-stopped`) |
| `nginx/nginx.conf`, `nginx/conf.d/loka.conf.template` | Reverse proxy HTTPS (HSTS, en-têtes de sécurité, gzip, rate limit sur `/api/v1/auth/`) |
| `nginx/conf.d/bootstrap.conf.template` | Config HTTP seule utilisée avant le premier certificat |
| `init-letsencrypt.sh` | Obtention du premier certificat (webroot ACME) |
| `deploy.sh` | Déploiement idempotent : pull, migrations, collectstatic, up, healthchecks, revalidation ISR, rollback automatique |
| `.env.prod.example` | Toutes les variables de prod, commentées |
| `logrotate-docker.conf`, `backup-cron.example` | Filets de sécurité (rotation des logs Docker, dump quotidien) |

## 1. Prérequis

### Serveur

- VPS **2 vCPU / 4 Go de RAM / 40 Go SSD minimum** (Ubuntu 22.04 ou 24.04 LTS). Pour MinIO auto-hébergé, prévoir le disque en conséquence (photos ≈ 300 Ko par variante).
- Un nom de domaine (`DOMAIN`, ex. `loka.tn`) avec les enregistrements DNS **A** (et **AAAA** si IPv6) de `DOMAIN` et `www.DOMAIN` pointant vers l'IP du VPS. Attendre la propagation (`dig +short loka.tn`) avant `init-letsencrypt.sh`.
- Un accès au registre GitLab du projet : un **deploy token** (Settings › Repository › Deploy tokens, scope `read_registry`) ou un compte avec accès en lecture.

### Installation de Docker et de l'utilisateur `deploy`

```bash
# En root sur le VPS
apt-get update && apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg ufw git

# Docker Engine + plugin compose (dépôt officiel)
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
docker compose version   # >= v2.24

# Utilisateur non-root dédié au déploiement
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
mkdir -p /opt/loka && chown deploy:deploy /opt/loka

# Clé SSH de la CI (générée sur votre poste : ssh-keygen -t ed25519 -f ~/.ssh/loka_deploy -C loka-ci)
mkdir -p /home/deploy/.ssh && chmod 700 /home/deploy/.ssh
echo "ssh-ed25519 AAAA... loka-ci" >> /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys && chown -R deploy:deploy /home/deploy/.ssh
```

### Pare-feu et durcissement

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # idéalement restreint : ufw allow from <IP_admin> to any port 22
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# SSH : clés uniquement
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload ssh

# Optionnel : fail2ban (bannit les IP après échecs SSH répétés)
apt-get install -y fail2ban && systemctl enable --now fail2ban

# Mises à jour de sécurité automatiques
apt-get install -y unattended-upgrades && dpkg-reconfigure -plow unattended-upgrades
```

> Docker manipule iptables directement : les ports publiés par un conteneur contournent ufw. C'est pourquoi **seul nginx publie des ports** dans le compose ; postgres, redis, minio, api et web restent sur le réseau interne.

## 2. Première installation

Toutes les commandes suivantes s'exécutent **en tant que `deploy`**, dans `/opt/loka`.

### 2.1 Récupérer les fichiers de déploiement

```bash
# Option 1 : clone complet (pratique pour suivre les mises à jour d'infra)
git clone https://gitlab.com/<groupe>/loka.git /opt/loka/src
cp -r /opt/loka/src/infra/deploy/. /opt/loka/

# Option 2 : copie depuis votre poste
scp -r infra/deploy/. deploy@VPS:/opt/loka/

cd /opt/loka && chmod +x deploy.sh init-letsencrypt.sh
```

### 2.2 Créer `.env.prod` et générer les secrets

```bash
cp .env.prod.example .env.prod && chmod 600 .env.prod
```

Éditer `.env.prod` : remplacer chaque `loka.tn` par votre domaine et chaque `CHANGE_ME_*` par une valeur générée :

| Variable | Commande |
|---|---|
| `DJANGO_SECRET_KEY` | `openssl rand -hex 32` (≥ 50 caractères, sinon l'API refuse de démarrer) |
| `POSTGRES_PASSWORD` (et dans `DATABASE_URL`) | `openssl rand -hex 24` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | `openssl rand -hex 16` / `openssl rand -hex 32` (ou clés fournies par le S3 externe) |
| `REVALIDATE_SECRET` | `openssl rand -hex 32` |
| `BACKUP_ENCRYPTION_KEY` | Clé Fernet : `docker run --rm python:3.12-slim sh -c "pip install -q cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"` — **à conserver hors du serveur** |
| `KONNECT_WEBHOOK_TOKEN` | `openssl rand -hex 32` |
| `EMAIL_HOST_PASSWORD`, `KONNECT_API_KEY`, `KONNECT_WALLET_ID` | Fournis par les prestataires (voir `docs/payments.md`) |
| `REGISTRY_USER` / `REGISTRY_PASSWORD` | Deploy token GitLab (`read_registry`) |

Points d'attention :

- `DJANGO_ALLOWED_HOSTS` doit contenir le domaine, `localhost` (healthcheck interne) et `api` (appels SSR du front).
- `CORS_ALLOWED_ORIGINS` en HTTPS uniquement, `JWT_COOKIE_SECURE=1` : vérifiés au démarrage par `config.settings.prod`.
- `NEXT_PUBLIC_API_URL` est **figée au build** de l'image web par la CI (variable `NEXT_PUBLIC_API_URL`). La valeur dans `.env.prod` doit être identique.
- Stockage : `COMPOSE_PROFILES=minio` + `S3_ENDPOINT_URL=http://minio:9000` + `S3_PUBLIC_ENDPOINT_URL=https://DOMAIN/media` pour MinIO auto-hébergé ; sinon laisser `COMPOSE_PROFILES` vide et renseigner l'endpoint du S3 externe (les buckets `loka-public` en lecture anonyme et `loka-private` doivent alors être créés à la main).

### 2.3 Obtenir le certificat TLS

```bash
./init-letsencrypt.sh --staging   # test : vérifie DNS + défi ACME sans consommer le quota Let's Encrypt
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm certbot delete --cert-name loka.tn
./init-letsencrypt.sh             # certificat réel (ajouter --no-www si www.DOMAIN n'a pas de DNS)
curl -I https://loka.tn/healthz   # HTTP/2 200
```

Le script démarre nginx avec `bootstrap.conf.template` (HTTP seul), demande le certificat par webroot, puis recrée nginx avec `loka.conf.template` (HTTPS). Le conteneur `certbot` tente ensuite un renouvellement toutes les 12 h et nginx se recharge toutes les 6 h.

### 2.4 Premier déploiement

```bash
./deploy.sh --tag <SHA_court_du_pipeline>   # ex. ./deploy.sh --tag a1b2c3d4
```

Le script : se connecte au registre, tire les images, prépare les volumes, applique les migrations, exécute `collectstatic` (volume `django_static` servi par nginx sous `/django-static/`), lance `docker compose up -d`, attend les healthchecks, vérifie `https://DOMAIN/api/v1/health/` et `https://DOMAIN/`, déclenche la revalidation ISR de `/` et enregistre le tag dans `.deploy/current_tag`.

### 2.5 Compte administrateur et données géographiques

```bash
alias lc='docker compose --env-file .env.prod -f docker-compose.prod.yml'
lc exec api python manage.py createsuperuser
# Villes et quartiers (référentiel géo). `seed` charge AUSSI des biens et comptes de démo :
# à réserver à une pré-production. Pour la prod, importer uniquement le référentiel géo
# (voir docs/data-model.md) ou saisir les villes depuis l'admin Django.
lc exec api python manage.py seed --help
```

### 2.6 Vérifications

```bash
lc ps                                    # tous les services `healthy`
curl -s https://loka.tn/api/v1/health/   # {"status": "ok", ...}
curl -sI https://loka.tn/ | grep -i strict-transport   # HSTS présent
lc logs --tail=100 api web worker beat
```

Tester ensuite depuis un navigateur : inscription, connexion (cookie `loka_refresh` Secure), upload d'une photo, envoi d'une demande (email reçu), paiement (mode sandbox d'abord).

### Admin Django

Le préfixe `/admin` public est occupé par le back-office Next.js de l'équipe ; l'admin Django (`/admin/` côté API) n'est donc **pas exposé** par défaut. Les opérations courantes passent par le back-office Next ou par les commandes de gestion (`lc exec api python manage.py ...`, `shell`).

Si l'admin Django devient nécessaire, `nginx/conf.d/loka.conf.template` contient un bloc commenté `admin.${DOMAIN}` (proxy vers l'API, accès restreint par IP). Pour l'activer : créer l'enregistrement DNS `admin.DOMAIN`, ajouter le sous-domaine au certificat (`lc run --rm --entrypoint certbot certbot certonly --webroot -w /var/www/certbot -d DOMAIN -d www.DOMAIN -d admin.DOMAIN --expand`), décommenter le bloc en renseignant vos IP dans `allow`, ajouter `admin.DOMAIN` à `DJANGO_ALLOWED_HOSTS` et `https://admin.DOMAIN` à `CORS_ALLOWED_ORIGINS` (pour le CSRF), puis `lc up -d --force-recreate nginx api`. Un tunnel SSH direct vers gunicorn ne convient pas : sans `X-Forwarded-Proto: https`, `SECURE_SSL_REDIRECT` renvoie vers une URL HTTPS inexistante.

## 3. Mise à jour

### Via GitLab CI (recommandé)

1. Un push sur `main` (ou un tag) exécute `lint` → `test` → `build:api` / `build:web` qui poussent `$CI_REGISTRY_IMAGE/api:<sha>` et `/web:<sha>`.
2. Le job **`deploy:prod`** (stage `deploy`, manuel) se lance depuis l'interface Pipelines. Il se connecte en SSH au VPS et exécute `cd /opt/loka && ./deploy.sh --tag <sha>`.

Variables CI à définir (Settings › CI/CD › Variables, *protected* + *masked*) :

| Variable | Valeur |
|---|---|
| `DEPLOY_HOST` | IP ou nom du VPS |
| `DEPLOY_USER` | `deploy` (défaut) |
| `DEPLOY_SSH_KEY` | Clé privée **base64** : `base64 -w0 ~/.ssh/loka_deploy` |
| `DEPLOY_KNOWN_HOSTS` | `ssh-keyscan -H <IP_VPS> 2>/dev/null` |
| `DEPLOY_DOMAIN` | Domaine public (URL de l'environnement `production`) |
| `NEXT_PUBLIC_API_URL` | `https://DOMAIN/api/v1` (build de l'image web) |

### À la main

```bash
cd /opt/loka && ./deploy.sh --tag a1b2c3d4
./deploy.sh --tag a1b2c3d4 --no-migrate   # redéploiement sans migrations
```

Le script est idempotent : le relancer avec le même tag ne fait que re-pull, re-collectstatic et recréer les conteneurs modifiés.

### Migrations : règle forward-only

Le rollback ne touche **que les images**. Les migrations doivent donc être rétro-compatibles avec la version précédente (ajouter des colonnes nullables, ne jamais supprimer/renommer une colonne dans la même release que le code qui cesse de l'utiliser, déployer la suppression une release plus tard). Une migration destructrice se prépare avec une sauvegarde préalable (`docs/backups.md`).

## 4. Rollback

Automatique : si les healthchecks ou les requêtes HTTPS échouent après `up`, `deploy.sh` redéploie `.deploy/previous_tag`.

Manuel :

```bash
./deploy.sh --rollback          # revient à .deploy/previous_tag
./deploy.sh --tag <ancien_sha>  # ou tout tag encore présent dans le registre
cat .deploy/history.log         # historique des déploiements réussis
```

## 5. Sauvegardes et restauration

La sauvegarde applicative (dump PostgreSQL chiffré avec `BACKUP_ENCRYPTION_KEY`, déposé sur le bucket privé) est une tâche Celery beat. Procédures de vérification et de restauration : voir [docs/backups.md](backups.md). `infra/deploy/backup-cron.example` fournit en complément un dump local quotidien indépendant de Celery.

Rappel : le service `beat` utilise `PersistentScheduler` avec le fichier de planning dans le volume `celery_beat` ; ne lancer **qu'une seule** instance de beat.

## 6. Délivrabilité des emails

L'API envoie les emails transactionnels (validation d'inscription, demandes, réservations, réinitialisation de mot de passe) en SMTP via `EMAIL_*`. Un envoi direct depuis le VPS finit en spam : passer par un prestataire.

### Prestataires SMTP

| Prestataire | `EMAIL_HOST` | Port / TLS | Remarques |
|---|---|---|---|
| Brevo (ex-Sendinblue) | `smtp-relay.brevo.com` | 587, `EMAIL_USE_TLS=1` | 300 emails/jour gratuits, interface FR, DKIM en 2 CNAME |
| Mailgun (région EU) | `smtp.eu.mailgun.org` | 587, TLS | Login `postmaster@mg.DOMAIN`, sous-domaine d'envoi |
| Amazon SES (eu-west-1) | `email-smtp.eu-west-1.amazonaws.com` | 587, TLS | Sortir du sandbox SES avant la mise en prod ; identifiants SMTP dédiés |

`DEFAULT_FROM_EMAIL` doit utiliser une adresse du domaine authentifié (`no-reply@loka.tn`), jamais une adresse Gmail.

### Enregistrements DNS à créer

Remplacer `loka.tn` par `DOMAIN` et `<provider>` par le domaine SPF communiqué par le prestataire (`spf.brevo.com`, `mailgun.org`, `amazonses.com`).

| Type | Nom | Valeur |
|---|---|---|
| TXT (SPF) | `loka.tn` | `v=spf1 include:<provider> ~all` — **un seul** enregistrement SPF par domaine ; fusionner les `include:` si Google Workspace / Microsoft 365 est déjà présent |
| CNAME ou TXT (DKIM) | fourni par le prestataire, ex. `mail._domainkey.loka.tn` ou `brevo1._domainkey` | valeur exacte fournie (clé publique DKIM) |
| TXT (DMARC) | `_dmarc.loka.tn` | `v=DMARC1; p=quarantine; rua=mailto:dmarc@loka.tn; pct=100; adkim=r; aspf=r` |
| MX (optionnel, réponses) | `loka.tn` | MX du service de boîtes mail (Google Workspace, OVH...) pour recevoir les réponses à `contact@` |

Commencer par `p=none` pendant une semaine pour lire les rapports `rua`, puis passer à `p=quarantine`, puis `p=reject` une fois tous les flux authentifiés.

### Procédure de test

1. Vérifier la propagation : `dig TXT loka.tn +short`, `dig TXT _dmarc.loka.tn +short`, `dig CNAME <selecteur>._domainkey.loka.tn +short`.
2. Depuis le VPS, envoyer un email de test à l'adresse jetable fournie par [mail-tester.com](https://www.mail-tester.com) :
   ```bash
   lc exec api python manage.py shell -c "from django.core.mail import send_mail; send_mail('Test Loka', 'Test de délivrabilité', None, ['test-xxxxx@srv1.mail-tester.com'])"
   ```
3. Viser un score ≥ 9/10 : SPF `pass`, DKIM `pass`, DMARC aligné, pas de blacklist, lien de désinscription non requis pour du transactionnel.
4. Tester la réception réelle sur Gmail, Outlook et une boîte OVH/tunisienne, y compris le dossier spam.
5. Activer la journalisation des bounces chez le prestataire et surveiller le taux de rebond (< 2 %).

## 7. Supervision

- **Sentry** : renseigner `SENTRY_DSN` (api et web), `SENTRY_ENVIRONMENT=production` ; `SENTRY_RELEASE` est aligné sur le tag déployé par `deploy.sh`. Vérifier qu'une erreur volontaire (`lc exec api python -c "import sentry_sdk; sentry_sdk.capture_message('deploy test')"`) apparaît dans le projet Sentry.
- **Logs** : `lc logs -f --tail=200 api`, `lc logs worker`, `lc logs nginx` (accès + erreurs, avec `rt=` temps de réponse). Rotation : json-file 5 × 10 Mo par conteneur, plus `sudo cp infra/deploy/logrotate-docker.conf /etc/logrotate.d/docker` en filet de sécurité.
- **Santé** : `lc ps` (colonne STATUS), `https://DOMAIN/api/v1/health/`, `https://DOMAIN/healthz` (nginx).
- **Disque** : `df -h /`, `docker system df`. Nettoyage : `docker image prune -af --filter "until=168h"`, `docker builder prune`. Le volume `postgres_data` et `minio_data` grossissent avec l'usage : surveiller à 85 %.
- **Ressources** : `docker stats --no-stream` ; si gunicorn sature, augmenter `GUNICORN_WORKERS` (2 × vCPU + 1) et la RAM.
- **Uptime externe** : sonde HTTPS toutes les minutes sur `/api/v1/health/` et `/` (UptimeRobot, Better Stack, Uptime Kuma auto-hébergé) avec alerte email/Telegram.
- **Certificat** : `lc run --rm --entrypoint certbot certbot certificates` (expiration), `echo | openssl s_client -connect DOMAIN:443 2>/dev/null | openssl x509 -noout -dates`.

## 8. Checklist de mise en production

- [ ] Tous les `CHANGE_ME_*` de `.env.prod` remplacés ; secrets générés avec `openssl rand`, `.env.prod` en `chmod 600`, copie des secrets dans un gestionnaire de mots de passe (dont `BACKUP_ENCRYPTION_KEY`).
- [ ] `DJANGO_SETTINGS_MODULE=config.settings.prod`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS` strict, `CORS_ALLOWED_ORIGINS` en HTTPS, `JWT_COOKIE_SECURE=1`.
- [ ] HTTPS : certificat réel (pas staging), redirection HTTP → HTTPS, HSTS présent, note A sur [ssllabs.com](https://www.ssllabs.com/ssltest/).
- [ ] Sauvegardes : tâche beat active, un dump restauré avec succès sur une base de test (`docs/backups.md`), cron de secours installé.
- [ ] Sentry reçoit les événements api et web, release = tag déployé.
- [ ] Paiement : `PAYMENT_PROVIDER=konnect`, `KONNECT_SANDBOX=0`, clés live, un paiement réel de faible montant testé puis remboursé ; webhooks joignables.
- [ ] Emails : SPF / DKIM / DMARC en place, score mail-tester ≥ 9, `DEFAULT_FROM_EMAIL` sur le domaine.
- [ ] Textes légaux remplacés (CGU, politique de confidentialité, mentions légales, gestion des données d'identité) et validés.
- [ ] Comptes : superutilisateur créé avec mot de passe fort, comptes de démo du `seed` absents, accès admin Django limité (tunnel SSH).
- [ ] Limitation de débit vérifiée : `for i in $(seq 1 25); do curl -s -o /dev/null -w '%{http_code}\n' -X POST https://DOMAIN/api/v1/auth/login/; done` renvoie des `429` après la rafale.
- [ ] Pare-feu ufw actif (22/80/443 uniquement), SSH par clé, fail2ban, mises à jour automatiques.
- [ ] Sonde d'uptime externe configurée avec alerte ; contact Let's Encrypt valide.
- [ ] `docs/deploy.md` et `.env.prod.example` à jour avec toute variable ajoutée depuis.


## Notes de migration par version

### Phase 6 (ADR 0007)

Après le premier déploiement de cette version, reconstruire l'instantané public des biens déjà publiés (une seule fois) :

```bash
docker compose -f docker-compose.prod.yml exec api python manage.py rebuild_snapshots
```

Puis vérifier les contenus provisoires :

```bash
docker compose -f docker-compose.prod.yml exec api python manage.py check --deploy
```
