# Rapport Phase 3 — Espace propriétaire

Commit : `fd16924`.

## Fait

- Inscription hôte (`/hote/inscription`) avec création automatique du profil hôte ; connexion, mot de passe oublié / réinitialisation (lien signé d'une heure), changement de mot de passe.
- Tableau de bord (`/hote`) : biens publiés / en validation, demandes en attente, réservations confirmées.
- Assistant de création en 6 étapes, brouillon sauvegardé à chaque étape : informations (typage strict, règles, équipements, distances), localisation (ville, quartier, adresse exacte privée, position sur carte cliquable, précision publique), photos (glisser-déposer, validation MIME et taille, réordonnancement, suppression, variantes WebP générées par Celery), tarifs par mode (nuit / mois / année avec durées min-max), calendrier (blocage de dates, import iCal HTTPS avec synchronisation horaire), publication (liste de complétude puis soumission).
- Cycle de vie visible : brouillon → en attente → visite → publié, pause / réactivation, retour en brouillon pour modification (nouvelle validation).
- Demandes reçues : accepter (crée la réservation et bloque les dates, refuse automatiquement les demandes concurrentes) ou refuser avec motif ; réservations avec annulation et contrat PDF signé.

## Tester

- `make e2e` (test `host-create.spec.ts`) ou manuellement avec `host@loka.tn` / `loka-host`.
- Permissions : un hôte ne voit que ses biens (404 sur les autres), un voyageur reçoit 403 (tests API `listings/tests/test_host_api.py`, `availability/tests/test_api.py`).

## Reste / questions ouvertes

- Vérification d'identité obligatoire avant publication : l'API ne l'impose pas encore (prudence : l'équipe décide au moment de la validation). À activer via une règle dans `listings.services.submit_for_review` si souhaité.
- Recadrage / rotation des photos côté client : non fait, l'orientation EXIF est corrigée côté API.
- Import iCal : parseur minimal (DTSTART / DTEND / UID) ; les calendriers exotiques peuvent nécessiter la librairie `icalendar`.
