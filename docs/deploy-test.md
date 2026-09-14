# Déploiement de test (Render + Vercel, sans nom de domaine)

Objectif : un environnement de démonstration public et réel, **gratuit**, sans nom de domaine.
Le back-end (API Django, PostGIS, Redis, stockage MinIO) tourne sur **Render** ; le front
Next.js sur **Vercel**. Les deux exposent des URLs HTTPS (`*.onrender.com`, `*.vercel.app`).

> Limites assumées pour rester gratuit :
> - **Celery synchrone** (`CELERY_TASK_ALWAYS_EAGER=1`) : le traitement des photos et l'envoi
>   des emails se font pendant la requête, sans worker séparé (payant sur Render).
> - **MinIO sans disque** : les fichiers sont perdus à la mise en veille du service ; il suffit
>   de relancer `seed`. Pour des photos persistantes, attacher un disque (option payante) —
>   bloc `disk:` commenté dans `render.yaml`.
> - **Services gratuits en veille** après 15 min d'inactivité (premier accès ~1 min).
> - **Authentification inter-domaines** (cookie de rafraîchissement `vercel.app` → `onrender.com`) :
>   les navigateurs peuvent bloquer ce cookie tiers. La navigation publique, les fiches, la carte
>   et le formulaire « Devenir hôte » fonctionnent ; la connexion peut être capricieuse. En
>   production réelle avec un seul domaine, ce point disparaît.

Le code est sur `github.com/ahmedsaadani/loka` (privé).

---

## 1. Back-end sur Render (blueprint `render.yaml`)

1. Créer un compte sur [render.com](https://render.com) (gratuit, connexion via GitHub).
2. **New › Blueprint**, autoriser l'accès au dépôt `ahmedsaadani/loka`, valider.
   Render lit `render.yaml` et crée quatre ressources : `loka-db` (PostgreSQL/PostGIS),
   `loka-redis`, `loka-minio`, `loka-api`.
3. Laisser le premier déploiement se faire. `loka-minio` et `loka-api` passent en « Live ».

### 1.a Relier l'API au stockage MinIO

1. Ouvrir le service **`loka-minio`** : copier son URL (`https://loka-minio-XXXX.onrender.com`).
2. Ouvrir **`loka-api` › Environment**, renseigner les deux variables laissées vides :
   - `S3_ENDPOINT_URL` = l'URL MinIO
   - `S3_PUBLIC_ENDPOINT_URL` = la même URL
3. **Save, rebuild** (« Manual Deploy › Deploy latest commit »).

### 1.b Charger les données de démonstration

Sur **`loka-api` › Shell** :

```bash
python manage.py seed
```

Le seed crée les comptes de test, les villes, les 33 biens et leurs photos (traitées en direct,
compter quelques minutes). Le compte admin est `admin@loka.tn` / `loka-admin`.

L'API est joignable sur `https://loka-api-XXXX.onrender.com/api/v1/health/` (doit répondre `200`).

---

## 2. Front sur Vercel

Le build du front fige l'URL de l'API : il se fait **après** que l'API Render existe.

1. Sur [vercel.com](https://vercel.com) : **Add New › Project**, importer `ahmedsaadani/loka`.
2. **Root Directory** : `apps/web`. Framework détecté : Next.js.
3. **Environment Variables** (Production) :

   | Variable | Valeur |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://loka-api-XXXX.onrender.com/api/v1` |
   | `API_INTERNAL_URL` | `https://loka-api-XXXX.onrender.com/api/v1` |
   | `NEXT_PUBLIC_SITE_URL` | (l'URL Vercel, connue après le 1er déploiement — y revenir) |
   | `NEXT_PUBLIC_S3_PUBLIC_URL` | `https://loka-minio-XXXX.onrender.com` |
   | `NEXT_PUBLIC_MAP_FALLBACK_OSM` | `1` (carte via OpenStreetMap, pour le test uniquement) |
   | `REVALIDATE_SECRET` | la valeur générée sur `loka-api` (Environment › `REVALIDATE_SECRET`, « Reveal ») |

4. **Deploy**. Récupérer l'URL publique `https://loka-XXXX.vercel.app`.
5. Revenir dans les variables Vercel, renseigner `NEXT_PUBLIC_SITE_URL` avec cette URL et
   **redéployer** (le SEO et les liens absolus l'utilisent).

> Alternative en ligne de commande (une fois `vercel login` fait) :
> `cd apps/web && vercel --prod` puis définir les variables via `vercel env add`.

---

## 3. Relier l'API au front (CORS + revalidation)

Sur **`loka-api` › Environment**, renseigner :

| Variable | Valeur |
|---|---|
| `CORS_ALLOWED_ORIGINS` | `https://loka-XXXX.vercel.app` |
| `SITE_URL` | `https://loka-XXXX.vercel.app` |
| `REVALIDATE_URL` | `https://loka-XXXX.vercel.app/api/revalidate` |

**Save, rebuild** `loka-api`. À partir de là, publier ou modifier un bien purge le cache du front.

---

## 4. Vérifications

- `https://loka-XXXX.vercel.app` : accueil, villes, une fiche, la recherche avec la carte (marqueurs regroupés).
- `/devenir-hote` : envoyer le formulaire ; le lead apparaît dans l'admin Django
  (`https://loka-api-XXXX.onrender.com/admin/`, compte `admin@loka.tn`).
- `/comment-ca-marche` : la page s'affiche.

## 5. Rappels

- Les services gratuits s'endorment : le premier accès après une pause est lent, c'est normal.
- Après une veille de MinIO, si des photos manquent, relancer `python manage.py seed` (§1.b).
- Ce montage à deux domaines est un environnement de **test**. Pour la vraie production
  (un seul domaine, HTTPS, worker Celery, sauvegardes, MapTiler), suivre `docs/deploy.md`.
