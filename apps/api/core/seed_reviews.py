"""Contenu de démonstration pour les avis voyageurs (noms + commentaires réalistes).

Ces données servent uniquement au jeu de démonstration : chaque avis est rattaché à une
réservation « terminée » créée par le seed. Aucun avis réel n'est fabriqué en production —
seuls les voyageurs ayant réellement séjourné peuvent en déposer via l'API.
"""

from __future__ import annotations

# Voyageurs fictifs (prénom, nom) qui laissent les avis de démonstration.
REVIEWER_NAMES: list[tuple[str, str]] = [
    ("Yassine", "Trabelsi"),
    ("Mariem", "Bouazizi"),
    ("Skander", "Gharbi"),
    ("Ines", "Chebbi"),
    ("Oussama", "Jaziri"),
    ("Rania", "Ben Youssef"),
    ("Wael", "Khelifi"),
    ("Sirine", "Mansour"),
    ("Nidhal", "Ferjani"),
    ("Emna", "Haddad"),
    ("Bilel", "Zouari"),
    ("Farah", "Slimani"),
]

# Commentaires par palier de note. Le seed pioche selon la note tirée.
COMMENTS: dict[int, list[str]] = {
    5: [
        "Séjour parfait, le logement est exactement comme sur les photos. Hôte très réactif.",
        "Impeccable et très propre. Quartier calme et bien situé, je recommande vivement.",
        "Tout était nickel, de l'accueil au départ. On reviendra sans hésiter.",
        "Excellent rapport qualité-prix, appartement lumineux et bien équipé.",
        "Rien à redire : literie confortable, cuisine complète, wifi rapide. Merci !",
        "Un vrai coup de cœur. Propre, chaleureux et proche de tout.",
    ],
    4: [
        "Très bon séjour dans l'ensemble, logement conforme et bien tenu.",
        "Agréable et bien placé. Petit bémol sur le bruit de la rue le matin.",
        "Bon accueil et logement propre. La déco gagnerait à être rafraîchie.",
        "Confortable et fonctionnel, je recommande pour un séjour en famille.",
        "Bien situé et calme. La connexion wifi était un peu lente par moments.",
        "Séjour satisfaisant, hôte disponible et logement conforme à l'annonce.",
    ],
    3: [
        "Correct pour le prix. Quelques détails d'entretien à revoir.",
        "Emplacement pratique mais le logement est un peu plus petit qu'attendu.",
        "Séjour convenable dans l'ensemble, sans plus. L'eau chaude était capricieuse.",
        "Ça dépanne bien, propre mais l'insonorisation laisse à désirer.",
    ],
}
