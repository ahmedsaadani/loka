"""
Catalogue des biens de démonstration (commande `seed`).

Données fictives mais réalistes : quartiers réels du Grand Tunis, de Sousse et de Hammamet,
prix alignés sur le marché tunisien 2026 (DT), photos libres de droits de la banque locale
`seed/photos/` (voir CREDITS.md). Aucun bien réel n'est décrit ici.
"""

# ruff: noqa: E501  (prose : descriptions longues, données de démo)
from __future__ import annotations

from typing import Any, TypedDict

# ------------------------------------------------------------------ géographie

GEO: dict[str, dict[str, Any]] = {
    "Ariana": {
        "gov": "Ariana",
        "centroid": (10.1647, 36.8625),
        "featured": True,
        "neighborhoods": {
            "Ghazela": (10.1875, 36.8975),
            "Ennasr": (10.1560, 36.8560),
            "Menzah 6": (10.1620, 36.8460),
            "Borj Louzir": (10.1900, 36.8840),
        },
    },
    "Tunis": {
        "gov": "Tunis",
        "centroid": (10.1815, 36.8065),
        "featured": True,
        "neighborhoods": {
            "Lac 2": (10.2560, 36.8390),
            "La Marsa": (10.3250, 36.8780),
            "Bardo": (10.1400, 36.8090),
            "Mutuelleville": (10.1760, 36.8300),
        },
    },
    "Sousse": {
        "gov": "Sousse",
        "centroid": (10.6400, 35.8250),
        "featured": True,
        "neighborhoods": {
            "Sahloul": (10.5950, 35.8400),
            "Kantaoui": (10.5990, 35.8900),
        },
    },
    "Hammamet": {
        "gov": "Nabeul",
        "centroid": (10.6167, 36.4000),
        "featured": True,
        "neighborhoods": {
            "Hammamet Nord": (10.5980, 36.4230),
            "Yasmine Hammamet": (10.5420, 36.3690),
            "Hammamet Centre": (10.6120, 36.4020),
        },
    },
}

# ------------------------------------------------------------------ équipements

AMENITIES = [
    ("wifi", "Wi-Fi fibre", "wifi", "essential", 1),
    ("ac", "Climatisation", "snowflake", "essential", 2),
    ("heating", "Chauffage", "flame", "essential", 3),
    ("kitchen", "Cuisine équipée", "cooking-pot", "essential", 4),
    ("water_heater", "Chauffe-eau", "droplets", "essential", 5),
    ("washer", "Lave-linge", "washing-machine", "comfort", 10),
    ("dishwasher", "Lave-vaisselle", "utensils", "comfort", 11),
    ("tv", "Télévision", "tv", "comfort", 12),
    ("desk", "Espace de travail", "laptop", "comfort", 13),
    ("balcony", "Balcon", "sun", "comfort", 14),
    ("terrace", "Terrasse", "sun", "comfort", 15),
    ("sea_view", "Vue mer", "waves", "comfort", 16),
    ("pool", "Piscine privée", "waves", "comfort", 17),
    ("garden", "Jardin", "trees", "comfort", 18),
    ("bbq", "Barbecue", "flame", "comfort", 19),
    ("parking", "Parking", "car", "building", 20),
    ("elevator", "Ascenseur", "arrow-up-down", "building", 21),
    ("intercom", "Interphone", "phone", "building", 22),
    ("security", "Gardien / sécurité", "shield-check", "safety", 30),
    ("smoke_detector", "Détecteur de fumée", "siren", "safety", 31),
    ("safe", "Coffre-fort", "lock", "safety", 32),
]

# ------------------------------------------------------------------ photos

# Textes alternatifs (FR) par catégorie de photo ; la variante est choisie par le seed.
PHOTO_ALT: dict[str, list[str]] = {
    "salon": [
        "Séjour lumineux avec canapé et table basse",
        "Salon meublé ouvert sur la terrasse",
        "Pièce à vivre avec coin salon et rangements",
        "Salon avec grandes fenêtres et lumière naturelle",
    ],
    "chambre": [
        "Chambre avec lit double et linge de lit fourni",
        "Chambre calme avec table de chevet et lampe",
        "Chambre principale lumineuse",
        "Chambre avec lit double face à la fenêtre",
    ],
    "cuisine": [
        "Cuisine équipée avec plaques, four et réfrigérateur",
        "Cuisine ouverte avec plan de travail et rangements",
        "Cuisine moderne avec îlot et tabourets",
        "Coin cuisine équipé, vaisselle fournie",
    ],
    "salle_de_bain": [
        "Salle de bain avec douche à l'italienne",
        "Salle de bain carrelée avec vasque et miroir",
        "Salle de bain avec baignoire et WC",
        "Salle d'eau rénovée",
    ],
    "balcon_vue": [
        "Vue dégagée depuis le balcon",
        "Terrasse avec vue sur la mer",
        "Balcon ensoleillé avec table et chaises",
        "Vue depuis la terrasse au coucher du soleil",
    ],
    "facade": [
        "Façade de la résidence",
        "Immeuble récent avec balcons et palmiers",
        "Entrée de la résidence, façade blanche",
        "Vue extérieure de l'immeuble",
    ],
    "villa_piscine": [
        "Piscine privée de la villa",
        "Bassin et transats côté jardin",
        "Piscine à débordement avec vue sur la mer",
        "Terrasse de la piscine en fin de journée",
    ],
    "villa_exterieur": [
        "Façade de la villa et jardin",
        "Extérieur de la villa, murs blancs et oliviers",
        "Entrée de la villa côté jardin",
        "Villa vue depuis l'allée",
    ],
    "studio": [
        "Studio meublé avec coin nuit et coin repas",
        "Pièce principale du studio, lit et bureau",
        "Studio avec kitchenette ouverte",
        "Espace de vie du studio",
    ],
    "chambre_etudiante": [
        "Chambre privée avec lit et bureau",
        "Chambre étudiante meublée, bureau côté fenêtre",
        "Chambre en colocation avec espace de travail",
        "Chambre calme avec lit simple et rangements",
    ],
}

# Plans de photos par type : catégorie de la couverture en premier.
PHOTO_PLANS: dict[str, list[str]] = {
    "studio": ["studio", "studio", "cuisine", "salle_de_bain", "facade"],
    "s1": ["salon", "chambre", "cuisine", "salle_de_bain", "balcon_vue", "facade"],
    "s2": ["salon", "chambre", "chambre", "cuisine", "salle_de_bain", "balcon_vue", "facade"],
    "s3": [
        "salon",
        "chambre",
        "chambre",
        "cuisine",
        "salle_de_bain",
        "balcon_vue",
        "facade",
        "salon",
    ],
    "villa_pool": [
        "villa_exterieur",
        "villa_piscine",
        "salon",
        "chambre",
        "chambre",
        "cuisine",
        "salle_de_bain",
        "balcon_vue",
    ],
    "villa": [
        "villa_exterieur",
        "salon",
        "chambre",
        "chambre",
        "cuisine",
        "salle_de_bain",
        "balcon_vue",
    ],
    "room": ["salon", "chambre_etudiante", "chambre_etudiante", "cuisine", "salle_de_bain"],
}


class SeedProperty(TypedDict, total=False):
    key: str
    type: str  # studio | apartment | villa | room_in_shared_flat
    label: str  # S+1, S+2… (rooms_label) ou vide
    plan: str  # clé de PHOTO_PLANS
    city: str
    neighborhood: str
    title: str
    description: str
    bedrooms: int
    bathrooms: int
    surface: int
    floor: int | None
    elevator: bool
    guests: int
    grade: str  # basic | good | excellent
    level: str  # verified | selection
    monthly: int | None
    nightly: int | None
    yearly: int | None  # prix annuel (ADR 0007)
    amenities: list[str]
    distances: dict[str, str]
    charges_included: bool
    charges: int
    deposit: int
    min_lease: int
    rules: dict[str, bool]


# ------------------------------------------------------------------ catalogue

_RULES = {"smoking": False, "pets": False, "parties": False}
_RULES_PETS = {"smoking": False, "pets": True, "parties": False}

PROPERTIES: list[SeedProperty] = [
    # ---------------------------------------------------------------- Ariana
    {
        "key": "ghazela-studio-esprit",
        "type": "studio",
        "label": "",
        "plan": "studio",
        "city": "Ariana",
        "neighborhood": "Ghazela",
        "title": "Studio meublé à 5 min à pied d'ESPRIT",
        "description": (
            "Studio de 30 m² au 2e étage d'un petit immeuble calme de la cité Ghazela, à cinq minutes "
            "à pied d'ESPRIT et des arrêts de bus vers le centre. Il comprend un lit double, un bureau, "
            "une kitchenette équipée (plaques, réfrigérateur, micro-ondes) et une salle d'eau avec douche.\n\n"
            "Le studio est loué meublé, avec la climatisation réversible et le Wi-Fi fibre inclus. "
            "Idéal pour un étudiant ou un jeune actif ; bail de 6 mois minimum, caution d'un mois."
        ),
        "bedrooms": 0,
        "bathrooms": 1,
        "surface": 30,
        "floor": 2,
        "elevator": False,
        "guests": 1,
        "grade": "good",
        "level": "verified",
        "monthly": 450,
        "nightly": None,
        "yearly": 5100,
        "amenities": ["wifi", "ac", "kitchen", "water_heater", "desk", "intercom"],
        "distances": {
            "ESPRIT": "5 min à pied",
            "Bus vers Tunis": "3 min à pied",
            "Supermarché": "4 min à pied",
        },
        "charges_included": False,
        "charges": 60,
        "deposit": 1,
        "min_lease": 6,
        "rules": _RULES,
    },
    {
        "key": "ghazela-studio-neuf",
        "type": "studio",
        "label": "",
        "plan": "studio",
        "city": "Ariana",
        "neighborhood": "Ghazela",
        "title": "Studio neuf dans une résidence sécurisée, Ghazela",
        "description": (
            "Studio de 36 m² livré en 2025 dans une résidence gardée avec ascenseur et parking. "
            "Grande pièce lumineuse exposée sud, cuisine ouverte entièrement équipée (lave-linge inclus), "
            "salle de bain moderne avec douche à l'italienne.\n\n"
            "Prestations soignées : double vitrage, climatisation, interphone vidéo. Proche d'ESPRIT, "
            "de l'Université Centrale et du pôle technologique de Ghazela."
        ),
        "bedrooms": 0,
        "bathrooms": 1,
        "surface": 36,
        "floor": 4,
        "elevator": True,
        "guests": 2,
        "grade": "excellent",
        "level": "selection",
        "monthly": 590,
        "nightly": 55,
        "yearly": 6600,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "desk",
            "parking",
            "elevator",
            "security",
            "intercom",
        ],
        "distances": {
            "ESPRIT": "8 min à pied",
            "Pôle technologique": "10 min à pied",
            "Centre commercial": "5 min en voiture",
        },
        "charges_included": True,
        "charges": 80,
        "deposit": 1,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "ghazela-s1-lumineux",
        "type": "apartment",
        "label": "S+1",
        "plan": "s1",
        "city": "Ariana",
        "neighborhood": "Ghazela",
        "title": "S+1 lumineux avec balcon, proche des facultés",
        "description": (
            "Appartement S+1 de 58 m² au 3e étage avec ascenseur, composé d'un séjour avec balcon, "
            "d'une chambre avec lit double et placard, d'une cuisine équipée et d'une salle de bain.\n\n"
            "Meublé avec goût, climatisé, connexion fibre. Quartier vivant avec commerces, cafés et "
            "transports à proximité immédiate. Convient à un couple ou à deux colocataires."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 58,
        "floor": 3,
        "elevator": True,
        "guests": 2,
        "grade": "good",
        "level": "verified",
        "monthly": 750,
        "nightly": 70,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "balcony",
            "elevator",
        ],
        "distances": {
            "ESPRIT": "10 min à pied",
            "Université Centrale": "12 min à pied",
            "Monoprix": "6 min à pied",
        },
        "charges_included": False,
        "charges": 70,
        "deposit": 1,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "borj-louzir-s1-simple",
        "type": "apartment",
        "label": "S+1",
        "plan": "s1",
        "city": "Ariana",
        "neighborhood": "Borj Louzir",
        "title": "S+1 simple et fonctionnel à Borj Louzir",
        "description": (
            "S+1 de 52 m² au 1er étage d'un immeuble familial, à Borj Louzir. Séjour avec canapé et "
            "table, chambre avec lit double, cuisine séparée équipée du nécessaire, salle de bain avec "
            "chauffe-eau.\n\n"
            "Meubles en bon état sans être neufs : un logement honnête et bien situé, à un prix "
            "raisonnable. Arrêt de bus et taxis collectifs au pied de l'immeuble."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 52,
        "floor": 1,
        "elevator": False,
        "guests": 2,
        "grade": "basic",
        "level": "verified",
        "monthly": 620,
        "nightly": None,
        "yearly": 6900,
        "amenities": ["wifi", "kitchen", "water_heater", "tv"],
        "distances": {
            "ESPRIT": "15 min en bus",
            "Marché de Borj Louzir": "5 min à pied",
            "Pharmacie": "2 min à pied",
        },
        "charges_included": False,
        "charges": 50,
        "deposit": 1,
        "min_lease": 6,
        "rules": _RULES,
    },
    {
        "key": "ennasr-s2-lumineux",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Ariana",
        "neighborhood": "Ennasr",
        "title": "S+2 lumineux avec deux balcons, Ennasr 2",
        "description": (
            "Bel appartement S+2 de 95 m² au 4e étage avec ascenseur, à Ennasr 2, à deux pas de "
            "l'avenue Hédi Nouira. Séjour double exposition ouvert sur un balcon, deux chambres dont une "
            "avec balcon, cuisine équipée avec lave-linge, salle de bain et WC séparés.\n\n"
            "Climatisation dans toutes les pièces, parking en sous-sol, gardien. Commerces, banques et "
            "restaurants au pied de l'immeuble."
        ),
        "bedrooms": 2,
        "bathrooms": 1,
        "surface": 95,
        "floor": 4,
        "elevator": True,
        "guests": 4,
        "grade": "good",
        "level": "verified",
        "monthly": 1100,
        "nightly": 110,
        "yearly": 12600,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "balcony",
            "parking",
            "elevator",
            "security",
            "intercom",
        ],
        "distances": {
            "Avenue Hédi Nouira": "3 min à pied",
            "Carrefour Ennasr": "10 min à pied",
            "Centre-ville": "20 min en voiture",
        },
        "charges_included": False,
        "charges": 90,
        "deposit": 2,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "ennasr-s2-standing",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Ariana",
        "neighborhood": "Ennasr",
        "title": "S+2 haut standing rénové, résidence avec gardien",
        "description": (
            "S+2 de 105 m² entièrement rénové en 2025 : cuisine américaine avec îlot, lave-vaisselle "
            "et four encastré, deux chambres avec dressing, salle de bain en marbre avec douche et "
            "baignoire.\n\n"
            "Résidence récente avec gardien 24 h/24, ascenseur et place de parking attribuée. Idéal "
            "pour un cadre en mission ou une famille cherchant un logement clé en main à Ennasr."
        ),
        "bedrooms": 2,
        "bathrooms": 2,
        "surface": 105,
        "floor": 5,
        "elevator": True,
        "guests": 4,
        "grade": "excellent",
        "level": "selection",
        "monthly": 1280,
        "nightly": 130,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "desk",
            "balcony",
            "parking",
            "elevator",
            "security",
            "intercom",
            "smoke_detector",
        ],
        "distances": {
            "Avenue Hédi Nouira": "5 min à pied",
            "Clinique": "4 min en voiture",
            "Aéroport Tunis-Carthage": "15 min en voiture",
        },
        "charges_included": True,
        "charges": 120,
        "deposit": 2,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "ennasr-s3-famille",
        "type": "apartment",
        "label": "S+3",
        "plan": "s3",
        "city": "Ariana",
        "neighborhood": "Ennasr",
        "title": "Grand S+3 familial avec terrasse, Ennasr 1",
        "description": (
            "Appartement S+3 de 140 m² au dernier étage, avec une terrasse de 20 m² sans vis-à-vis. "
            "Séjour et salle à manger, trois chambres (deux lits doubles, deux lits simples), deux "
            "salles de bain, cuisine équipée avec lave-linge et lave-vaisselle.\n\n"
            "Immeuble avec ascenseur et parking. Écoles et jardins d'enfants à proximité, commerces "
            "au pied de la résidence. Loué meublé, au mois ou à l'année."
        ),
        "bedrooms": 3,
        "bathrooms": 2,
        "surface": 140,
        "floor": 6,
        "elevator": True,
        "guests": 6,
        "grade": "good",
        "level": "verified",
        "monthly": 1650,
        "nightly": 160,
        "yearly": 18600,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "terrace",
            "parking",
            "elevator",
            "intercom",
        ],
        "distances": {
            "École primaire": "5 min à pied",
            "Avenue Hédi Nouira": "8 min à pied",
            "Tunis centre": "25 min en voiture",
        },
        "charges_included": False,
        "charges": 110,
        "deposit": 2,
        "min_lease": 6,
        "rules": _RULES_PETS,
    },
    {
        "key": "menzah6-s2-a-rafraichir",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Ariana",
        "neighborhood": "Menzah 6",
        "title": "S+2 spacieux au calme, Menzah 6",
        "description": (
            "S+2 de 90 m² au 2e étage sans ascenseur, dans une rue calme du Menzah 6. Grand séjour, "
            "deux chambres avec placards, cuisine séparée, salle de bain avec baignoire.\n\n"
            "Le mobilier est simple mais complet, l'appartement est propre et bien entretenu ; la "
            "décoration date un peu, d'où un loyer contenu pour le quartier. Lignes de bus vers le "
            "centre et la Manouba à 200 m."
        ),
        "bedrooms": 2,
        "bathrooms": 1,
        "surface": 90,
        "floor": 2,
        "elevator": False,
        "guests": 4,
        "grade": "basic",
        "level": "verified",
        "monthly": 950,
        "nightly": None,
        "yearly": 10800,
        "amenities": ["wifi", "ac", "kitchen", "water_heater", "washer", "tv"],
        "distances": {
            "Bus centre-ville": "3 min à pied",
            "Faculté des sciences": "15 min en bus",
            "Marché": "6 min à pied",
        },
        "charges_included": False,
        "charges": 70,
        "deposit": 1,
        "min_lease": 6,
        "rules": _RULES,
    },
    {
        "key": "menzah6-s1-cosy",
        "type": "apartment",
        "label": "S+1",
        "plan": "s1",
        "city": "Ariana",
        "neighborhood": "Menzah 6",
        "title": "S+1 cosy avec balcon, Menzah 6",
        "description": (
            "S+1 de 60 m² au 3e étage avec ascenseur, entièrement remeublé en 2024. Séjour avec canapé "
            "convertible et balcon, chambre avec lit 160 cm, cuisine équipée, salle de bain avec douche.\n\n"
            "Fibre optique, climatisation réversible, télévision connectée. Quartier résidentiel calme "
            "avec commerces de proximité ; parking facile dans la rue."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 60,
        "floor": 3,
        "elevator": True,
        "guests": 3,
        "grade": "good",
        "level": "verified",
        "monthly": 820,
        "nightly": 80,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "balcony",
            "elevator",
            "intercom",
        ],
        "distances": {
            "Bus centre-ville": "5 min à pied",
            "Clinique": "5 min en voiture",
            "Supermarché": "3 min à pied",
        },
        "charges_included": False,
        "charges": 60,
        "deposit": 1,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "borj-louzir-s3-famille",
        "type": "apartment",
        "label": "S+3",
        "plan": "s3",
        "city": "Ariana",
        "neighborhood": "Borj Louzir",
        "title": "S+3 familial à prix doux, Borj Louzir",
        "description": (
            "Grand S+3 de 130 m² au 1er étage d'une maison divisée en deux appartements, avec entrée "
            "indépendante. Séjour, trois chambres, cuisine séparée, salle de bain et WC indépendants.\n\n"
            "Mobilier simple et complet, chauffe-eau, climatiseur dans le séjour. Proche des écoles et du "
            "marché de Borj Louzir ; le propriétaire habite au rez-de-chaussée et se montre disponible."
        ),
        "bedrooms": 3,
        "bathrooms": 1,
        "surface": 130,
        "floor": 1,
        "elevator": False,
        "guests": 6,
        "grade": "basic",
        "level": "verified",
        "monthly": 1150,
        "nightly": None,
        "yearly": 12600,
        "amenities": ["wifi", "ac", "kitchen", "water_heater", "washer", "tv", "parking"],
        "distances": {
            "École": "4 min à pied",
            "Marché de Borj Louzir": "6 min à pied",
            "ESPRIT": "12 min en bus",
        },
        "charges_included": False,
        "charges": 80,
        "deposit": 1,
        "min_lease": 12,
        "rules": _RULES_PETS,
    },
    # ---------------------------------------------------------------- Tunis
    {
        "key": "lac2-s2-vue-lac",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Tunis",
        "neighborhood": "Lac 2",
        "title": "S+2 moderne avec vue sur le lac, Les Berges du Lac 2",
        "description": (
            "S+2 de 110 m² au 7e étage d'une résidence de standing aux Berges du Lac 2, avec vue "
            "dégagée sur le lac depuis le séjour et la terrasse. Cuisine ouverte équipée (lave-vaisselle, "
            "four, plaques à induction), deux chambres avec dressing, deux salles de bain.\n\n"
            "Résidence avec gardien, deux ascenseurs, parking en sous-sol et salle de sport. À proximité "
            "des sièges d'entreprises, des ambassades et du Tunisia Mall."
        ),
        "bedrooms": 2,
        "bathrooms": 2,
        "surface": 110,
        "floor": 7,
        "elevator": True,
        "guests": 4,
        "grade": "excellent",
        "level": "selection",
        "monthly": 1900,
        "nightly": 170,
        "yearly": 21600,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "desk",
            "terrace",
            "parking",
            "elevator",
            "security",
            "intercom",
            "smoke_detector",
            "safe",
        ],
        "distances": {
            "Tunisia Mall": "8 min à pied",
            "Aéroport": "12 min en voiture",
            "Centre-ville": "15 min en voiture",
        },
        "charges_included": True,
        "charges": 150,
        "deposit": 2,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "lac2-s1-executive",
        "type": "apartment",
        "label": "S+1",
        "plan": "s1",
        "city": "Tunis",
        "neighborhood": "Lac 2",
        "title": "S+1 executive tout équipé, Lac 2",
        "description": (
            "S+1 de 65 m² pensé pour les séjours professionnels : bureau ergonomique, fibre, "
            "télévision connectée, cuisine équipée avec machine à café, literie hôtelière.\n\n"
            "Résidence sécurisée avec parking et ascenseur, à cinq minutes à pied des tours de "
            "bureaux du Lac 2. Ménage hebdomadaire possible en option."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 65,
        "floor": 3,
        "elevator": True,
        "guests": 2,
        "grade": "excellent",
        "level": "verified",
        "monthly": 1450,
        "nightly": 140,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "desk",
            "balcony",
            "parking",
            "elevator",
            "security",
            "safe",
        ],
        "distances": {
            "Tours du Lac": "5 min à pied",
            "Tunisia Mall": "10 min à pied",
            "Aéroport": "12 min en voiture",
        },
        "charges_included": True,
        "charges": 120,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES,
    },
    {
        "key": "marsa-s2-plage",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Tunis",
        "neighborhood": "La Marsa",
        "title": "S+2 à 5 min de la plage, La Marsa Plage",
        "description": (
            "S+2 de 88 m² au 2e étage d'un immeuble blanc typique de La Marsa, à cinq minutes à pied "
            "de la plage et de la corniche. Séjour clair avec balcon, deux chambres, cuisine équipée, "
            "salle de bain avec douche.\n\n"
            "Ambiance bord de mer, cafés et restaurants à proximité, TGM à dix minutes. Loué au mois "
            "hors saison et à la nuit en été."
        ),
        "bedrooms": 2,
        "bathrooms": 1,
        "surface": 88,
        "floor": 2,
        "elevator": False,
        "guests": 4,
        "grade": "good",
        "level": "verified",
        "monthly": 1500,
        "nightly": 150,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "balcony",
            "intercom",
        ],
        "distances": {
            "Plage": "5 min à pied",
            "Station TGM": "10 min à pied",
            "Corniche": "6 min à pied",
        },
        "charges_included": False,
        "charges": 90,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES,
    },
    {
        "key": "marsa-s3-terrasse",
        "type": "apartment",
        "label": "S+3",
        "plan": "s3",
        "city": "Tunis",
        "neighborhood": "La Marsa",
        "title": "S+3 de standing avec grande terrasse, La Marsa",
        "description": (
            "Appartement S+3 de 150 m² au dernier étage d'une résidence récente de La Marsa, avec une "
            "terrasse de 40 m² et vue mer partielle. Vaste séjour, cuisine ouverte entièrement équipée, "
            "trois chambres, deux salles de bain, buanderie.\n\n"
            "Ascenseur, parking en sous-sol, gardien. Idéal pour une famille ou pour un séjour d'été "
            "à quelques minutes des plages de La Marsa et de Gammarth."
        ),
        "bedrooms": 3,
        "bathrooms": 2,
        "surface": 150,
        "floor": 4,
        "elevator": True,
        "guests": 6,
        "grade": "excellent",
        "level": "selection",
        "monthly": 2300,
        "nightly": 240,
        "yearly": 26400,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "terrace",
            "sea_view",
            "parking",
            "elevator",
            "security",
            "intercom",
            "smoke_detector",
        ],
        "distances": {
            "Plage": "8 min à pied",
            "Gammarth": "10 min en voiture",
            "Lycée français": "5 min en voiture",
        },
        "charges_included": False,
        "charges": 140,
        "deposit": 2,
        "min_lease": 1,
        "rules": _RULES,
    },
    {
        "key": "marsa-studio-cosy",
        "type": "studio",
        "label": "",
        "plan": "studio",
        "city": "Tunis",
        "neighborhood": "La Marsa",
        "title": "Studio cosy à deux pas du TGM, La Marsa",
        "description": (
            "Studio de 32 m² au rez-de-chaussée surélevé d'une petite résidence, à 300 m de la station "
            "TGM de La Marsa. Coin nuit avec lit double, coin salon, kitchenette équipée, salle d'eau.\n\n"
            "Climatisé, fibre incluse. Parfait pour une personne seule travaillant à Tunis ou pour un "
            "séjour de quelques semaines au bord de la mer."
        ),
        "bedrooms": 0,
        "bathrooms": 1,
        "surface": 32,
        "floor": 0,
        "elevator": False,
        "guests": 2,
        "grade": "good",
        "level": "verified",
        "monthly": 780,
        "nightly": 75,
        "yearly": None,
        "amenities": ["wifi", "ac", "kitchen", "water_heater", "tv", "desk"],
        "distances": {
            "Station TGM": "4 min à pied",
            "Plage": "10 min à pied",
            "Marché": "5 min à pied",
        },
        "charges_included": True,
        "charges": 60,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES,
    },
    {
        "key": "bardo-s1-metro",
        "type": "apartment",
        "label": "S+1",
        "plan": "s1",
        "city": "Tunis",
        "neighborhood": "Bardo",
        "title": "S+1 à 3 min du métro, Le Bardo",
        "description": (
            "S+1 de 50 m² au 1er étage, à trois minutes à pied de la station de métro Le Bardo "
            "(ligne 4) et à dix minutes du musée. Séjour, chambre avec lit double, cuisine séparée, "
            "salle de bain avec chauffe-eau.\n\n"
            "Logement simple et propre, mobilier fonctionnel, bien desservi pour rejoindre le centre "
            "de Tunis ou le campus de la Manouba. Loyer modéré, bail de 6 mois minimum."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 50,
        "floor": 1,
        "elevator": False,
        "guests": 2,
        "grade": "basic",
        "level": "verified",
        "monthly": 600,
        "nightly": None,
        "yearly": 6600,
        "amenities": ["wifi", "kitchen", "water_heater", "tv"],
        "distances": {
            "Métro Le Bardo": "3 min à pied",
            "Musée du Bardo": "10 min à pied",
            "Campus Manouba": "15 min en métro",
        },
        "charges_included": False,
        "charges": 50,
        "deposit": 1,
        "min_lease": 6,
        "rules": _RULES,
    },
    {
        "key": "bardo-s2-renove",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Tunis",
        "neighborhood": "Bardo",
        "title": "S+2 rénové et climatisé, Bardo",
        "description": (
            "S+2 de 85 m² au 3e étage, rénové en 2024 : peinture, cuisine et salle de bain neuves. "
            "Séjour avec balcon, deux chambres climatisées, cuisine équipée avec lave-linge.\n\n"
            "Quartier calme et résidentiel, à cinq minutes du métro et des commerces. Convient à une "
            "petite famille ou à des colocataires."
        ),
        "bedrooms": 2,
        "bathrooms": 1,
        "surface": 85,
        "floor": 3,
        "elevator": False,
        "guests": 4,
        "grade": "good",
        "level": "verified",
        "monthly": 850,
        "nightly": None,
        "yearly": 9600,
        "amenities": ["wifi", "ac", "kitchen", "water_heater", "washer", "tv", "balcony"],
        "distances": {
            "Métro": "5 min à pied",
            "Musée du Bardo": "12 min à pied",
            "Supermarché": "3 min à pied",
        },
        "charges_included": False,
        "charges": 70,
        "deposit": 1,
        "min_lease": 6,
        "rules": _RULES,
    },
    {
        "key": "mutuelleville-s2-central",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Tunis",
        "neighborhood": "Mutuelleville",
        "title": "S+2 central et calme, Mutuelleville",
        "description": (
            "S+2 de 92 m² au 2e étage avec ascenseur, dans une rue arborée de Mutuelleville. Séjour "
            "avec balcon, deux chambres, cuisine équipée, salle de bain avec baignoire et WC séparés.\n\n"
            "Emplacement idéal : à dix minutes à pied du centre-ville, des cliniques et des facultés "
            "de médecine et de pharmacie. Parking gardé à 50 m."
        ),
        "bedrooms": 2,
        "bathrooms": 1,
        "surface": 92,
        "floor": 2,
        "elevator": True,
        "guests": 4,
        "grade": "good",
        "level": "verified",
        "monthly": 1200,
        "nightly": 115,
        "yearly": 13800,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "balcony",
            "elevator",
            "intercom",
        ],
        "distances": {
            "Faculté de médecine": "10 min à pied",
            "Avenue Habib Bourguiba": "15 min à pied",
            "Clinique": "5 min à pied",
        },
        "charges_included": False,
        "charges": 90,
        "deposit": 1,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "mutuelleville-s1-neuf",
        "type": "apartment",
        "label": "S+1",
        "plan": "s1",
        "city": "Tunis",
        "neighborhood": "Mutuelleville",
        "title": "S+1 neuf avec parking, Mutuelleville",
        "description": (
            "S+1 de 62 m² dans une résidence livrée en 2025, au 4e étage avec ascenseur. Séjour avec "
            "cuisine ouverte équipée (lave-vaisselle, four), chambre avec dressing, salle de bain avec "
            "douche à l'italienne, balcon.\n\n"
            "Place de parking en sous-sol, interphone vidéo, climatisation réversible. Quartier "
            "central, calme et bien desservi."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 62,
        "floor": 4,
        "elevator": True,
        "guests": 2,
        "grade": "excellent",
        "level": "verified",
        "monthly": 950,
        "nightly": 95,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "desk",
            "balcony",
            "parking",
            "elevator",
            "intercom",
            "smoke_detector",
        ],
        "distances": {
            "Centre-ville": "15 min à pied",
            "Faculté de médecine": "8 min à pied",
            "Métro": "10 min à pied",
        },
        "charges_included": False,
        "charges": 80,
        "deposit": 1,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "mutuelleville-studio-facs",
        "type": "studio",
        "label": "",
        "plan": "studio",
        "city": "Tunis",
        "neighborhood": "Mutuelleville",
        "title": "Studio proche des facultés et des cliniques",
        "description": (
            "Studio de 28 m² au 2e étage, à cinq minutes à pied de la faculté de médecine et des "
            "grandes cliniques de Mutuelleville. Lit double, bureau, kitchenette équipée, salle d'eau.\n\n"
            "Climatisé, Wi-Fi inclus, immeuble calme. Adapté à un étudiant en médecine, un interne ou "
            "un professionnel de santé en mission."
        ),
        "bedrooms": 0,
        "bathrooms": 1,
        "surface": 28,
        "floor": 2,
        "elevator": False,
        "guests": 1,
        "grade": "good",
        "level": "verified",
        "monthly": 650,
        "nightly": 60,
        "yearly": 7200,
        "amenities": ["wifi", "ac", "kitchen", "water_heater", "desk", "tv"],
        "distances": {
            "Faculté de médecine": "5 min à pied",
            "Clinique": "3 min à pied",
            "Métro": "8 min à pied",
        },
        "charges_included": True,
        "charges": 50,
        "deposit": 1,
        "min_lease": 3,
        "rules": _RULES,
    },
    # ---------------------------------------------------------------- Sousse
    {
        "key": "sahloul-s2-familial",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Sousse",
        "neighborhood": "Sahloul",
        "title": "S+2 familial bien situé, Sahloul 4",
        "description": (
            "S+2 de 96 m² au 3e étage avec ascenseur, à Sahloul 4, à cinq minutes de l'hôpital "
            "Sahloul et des commerces de l'avenue Yasser Arafat. Séjour avec balcon, deux chambres, "
            "cuisine équipée, salle de bain.\n\n"
            "Climatisation, chauffe-eau, lave-linge. Quartier familial et animé, plages à dix minutes "
            "en voiture."
        ),
        "bedrooms": 2,
        "bathrooms": 1,
        "surface": 96,
        "floor": 3,
        "elevator": True,
        "guests": 4,
        "grade": "good",
        "level": "verified",
        "monthly": 950,
        "nightly": 100,
        "yearly": 10800,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "balcony",
            "elevator",
            "parking",
        ],
        "distances": {
            "Hôpital Sahloul": "5 min à pied",
            "Plage": "10 min en voiture",
            "Supermarché": "3 min à pied",
        },
        "charges_included": False,
        "charges": 70,
        "deposit": 1,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "sahloul-s1-simple",
        "type": "apartment",
        "label": "S+1",
        "plan": "s1",
        "city": "Sousse",
        "neighborhood": "Sahloul",
        "title": "S+1 pratique à Sahloul, proche de l'ISET",
        "description": (
            "S+1 de 55 m² au 2e étage, à dix minutes à pied de l'ISET et de la faculté de médecine "
            "de Sousse. Séjour, chambre avec lit double, cuisine séparée, salle de bain.\n\n"
            "Meublé simplement, climatiseur dans la chambre, immeuble calme. Loyer accessible pour un "
            "étudiant ou un jeune couple ; bail de 6 mois minimum."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 55,
        "floor": 2,
        "elevator": False,
        "guests": 2,
        "grade": "basic",
        "level": "verified",
        "monthly": 680,
        "nightly": None,
        "yearly": 7500,
        "amenities": ["wifi", "ac", "kitchen", "water_heater", "tv"],
        "distances": {
            "ISET Sousse": "10 min à pied",
            "Faculté de médecine": "12 min à pied",
            "Bus": "3 min à pied",
        },
        "charges_included": False,
        "charges": 50,
        "deposit": 1,
        "min_lease": 6,
        "rules": _RULES,
    },
    {
        "key": "sahloul-s3-standing",
        "type": "apartment",
        "label": "S+3",
        "plan": "s3",
        "city": "Sousse",
        "neighborhood": "Sahloul",
        "title": "S+3 de standing dans une résidence neuve, Sahloul",
        "description": (
            "S+3 de 145 m² au 5e étage d'une résidence livrée en 2025, avec vue dégagée sur la ville. "
            "Grand séjour avec terrasse, trois chambres, deux salles de bain, cuisine équipée avec "
            "lave-vaisselle et four.\n\n"
            "Ascenseur, parking en sous-sol, gardien, double vitrage et climatisation dans toutes les "
            "pièces. Hôpital, écoles et commerces à moins de dix minutes."
        ),
        "bedrooms": 3,
        "bathrooms": 2,
        "surface": 145,
        "floor": 5,
        "elevator": True,
        "guests": 6,
        "grade": "excellent",
        "level": "selection",
        "monthly": 1350,
        "nightly": 140,
        "yearly": 15000,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "terrace",
            "parking",
            "elevator",
            "security",
            "intercom",
            "smoke_detector",
        ],
        "distances": {
            "Hôpital Sahloul": "8 min à pied",
            "Plage": "12 min en voiture",
            "Centre de Sousse": "15 min en voiture",
        },
        "charges_included": False,
        "charges": 110,
        "deposit": 2,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "kantaoui-s1-marina",
        "type": "apartment",
        "label": "S+1",
        "plan": "s1",
        "city": "Sousse",
        "neighborhood": "Kantaoui",
        "title": "S+1 avec vue sur la marina, Port El Kantaoui",
        "description": (
            "S+1 de 60 m² au 3e étage d'une résidence balnéaire de Port El Kantaoui, avec balcon "
            "donnant sur la marina. Séjour avec canapé-lit, chambre avec lit double, cuisine équipée, "
            "salle de bain.\n\n"
            "Résidence avec piscine commune, gardien et parking. Plage à 200 m, golf et restaurants "
            "à pied. Loué à la nuit en saison et au mois hors saison."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 60,
        "floor": 3,
        "elevator": True,
        "guests": 3,
        "grade": "excellent",
        "level": "selection",
        "monthly": 1150,
        "nightly": 145,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "balcony",
            "sea_view",
            "parking",
            "elevator",
            "security",
            "safe",
        ],
        "distances": {
            "Plage": "3 min à pied",
            "Marina": "2 min à pied",
            "Golf El Kantaoui": "5 min en voiture",
        },
        "charges_included": True,
        "charges": 90,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES,
    },
    {
        "key": "kantaoui-s2-piscine",
        "type": "apartment",
        "label": "S+2",
        "plan": "s2",
        "city": "Sousse",
        "neighborhood": "Kantaoui",
        "title": "S+2 en résidence avec piscine, Kantaoui",
        "description": (
            "S+2 de 85 m² en rez-de-jardin d'une résidence sécurisée avec piscine, à Port El Kantaoui. "
            "Séjour ouvert sur une terrasse privative, deux chambres, cuisine équipée, salle de bain.\n\n"
            "Climatisation, lave-linge, télévision. Accès direct à la piscine commune ; plage et "
            "commerces à cinq minutes à pied."
        ),
        "bedrooms": 2,
        "bathrooms": 1,
        "surface": 85,
        "floor": 0,
        "elevator": False,
        "guests": 5,
        "grade": "good",
        "level": "verified",
        "monthly": 1500,
        "nightly": 185,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "terrace",
            "parking",
            "security",
        ],
        "distances": {
            "Plage": "5 min à pied",
            "Marina": "8 min à pied",
            "Sousse centre": "15 min en voiture",
        },
        "charges_included": True,
        "charges": 100,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES_PETS,
    },
    # ---------------------------------------------------------------- villas
    {
        "key": "hammamet-nord-villa-piscine",
        "type": "villa",
        "label": "",
        "plan": "villa_pool",
        "city": "Hammamet",
        "neighborhood": "Hammamet Nord",
        "title": "Villa avec piscine privée et jardin, Hammamet Nord",
        "description": (
            "Villa de 260 m² sur un terrain clos de 900 m² à Hammamet Nord, à 600 m de la plage. "
            "Quatre chambres climatisées (trois lits doubles, deux lits simples), trois salles de bain, "
            "grand séjour ouvert sur la terrasse et la piscine de 10 × 5 m.\n\n"
            "Cuisine entièrement équipée, barbecue, pergola, parking pour trois voitures, gardien de "
            "nuit. Linge de maison et ménage de fin de séjour inclus. Loué à la nuit (minimum 3 nuits) "
            "ou au mois hors saison."
        ),
        "bedrooms": 4,
        "bathrooms": 3,
        "surface": 260,
        "floor": None,
        "elevator": False,
        "guests": 8,
        "grade": "excellent",
        "level": "selection",
        "monthly": 6000,
        "nightly": 420,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "terrace",
            "pool",
            "garden",
            "bbq",
            "parking",
            "security",
            "safe",
        ],
        "distances": {
            "Plage": "8 min à pied",
            "Centre d'Hammamet": "10 min en voiture",
            "Médina": "12 min en voiture",
        },
        "charges_included": True,
        "charges": 250,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES,
    },
    {
        "key": "yasmine-villa-piscine",
        "type": "villa",
        "label": "",
        "plan": "villa_pool",
        "city": "Hammamet",
        "neighborhood": "Yasmine Hammamet",
        "title": "Villa moderne avec piscine, Yasmine Hammamet",
        "description": (
            "Villa contemporaine de 200 m² dans un lotissement calme de Yasmine Hammamet, à dix "
            "minutes à pied de la marina. Trois chambres, deux salles de bain, séjour avec baies "
            "vitrées ouvertes sur la piscine et le jardin.\n\n"
            "Cuisine équipée avec lave-vaisselle, terrasse couverte, barbecue, parking fermé. Idéale "
            "pour une famille ou un groupe d'amis. Minimum 2 nuits."
        ),
        "bedrooms": 3,
        "bathrooms": 2,
        "surface": 200,
        "floor": None,
        "elevator": False,
        "guests": 6,
        "grade": "good",
        "level": "verified",
        "monthly": 4500,
        "nightly": 300,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "terrace",
            "pool",
            "garden",
            "bbq",
            "parking",
        ],
        "distances": {
            "Marina Yasmine": "10 min à pied",
            "Plage": "12 min à pied",
            "Carthage Land": "5 min en voiture",
        },
        "charges_included": True,
        "charges": 200,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES,
    },
    {
        "key": "hammamet-centre-villa-simple",
        "type": "villa",
        "label": "",
        "plan": "villa",
        "city": "Hammamet",
        "neighborhood": "Hammamet Centre",
        "title": "Villa simple à 300 m de la plage, Hammamet",
        "description": (
            "Villa de plain-pied de 150 m² avec jardin, à 300 m de la plage et à quinze minutes à "
            "pied de la médina d'Hammamet. Trois chambres, deux salles de bain, séjour, cuisine "
            "équipée, grande terrasse ombragée.\n\n"
            "Maison familiale au mobilier simple et bien entretenue, sans piscine. Un bon rapport "
            "qualité-prix pour des vacances en famille à Hammamet."
        ),
        "bedrooms": 3,
        "bathrooms": 2,
        "surface": 150,
        "floor": None,
        "elevator": False,
        "guests": 6,
        "grade": "basic",
        "level": "verified",
        "monthly": 3200,
        "nightly": 250,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "terrace",
            "garden",
            "parking",
        ],
        "distances": {"Plage": "4 min à pied", "Médina": "15 min à pied", "Gare": "10 min à pied"},
        "charges_included": True,
        "charges": 150,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES_PETS,
    },
    {
        "key": "kantaoui-villa-vue-mer",
        "type": "villa",
        "label": "",
        "plan": "villa_pool",
        "city": "Sousse",
        "neighborhood": "Kantaoui",
        "title": "Villa vue mer avec piscine à débordement, Kantaoui",
        "description": (
            "Villa d'architecte de 300 m² sur les hauteurs de Port El Kantaoui, avec vue panoramique "
            "sur la mer et piscine à débordement chauffée. Quatre suites avec salle de bain privative, "
            "double séjour, cuisine professionnelle, salle de cinéma.\n\n"
            "Personnel de maison à la demande, gardien, parking couvert. Golf et marina à cinq "
            "minutes. Minimum 3 nuits, caution demandée."
        ),
        "bedrooms": 4,
        "bathrooms": 4,
        "surface": 300,
        "floor": None,
        "elevator": False,
        "guests": 8,
        "grade": "excellent",
        "level": "selection",
        "monthly": None,
        "nightly": 480,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "desk",
            "terrace",
            "sea_view",
            "pool",
            "garden",
            "bbq",
            "parking",
            "security",
            "smoke_detector",
            "safe",
        ],
        "distances": {
            "Plage": "10 min à pied",
            "Golf El Kantaoui": "5 min en voiture",
            "Aéroport Enfidha": "35 min en voiture",
        },
        "charges_included": True,
        "charges": 300,
        "deposit": 1,
        "min_lease": 1,
        "rules": _RULES,
    },
    {
        "key": "marsa-villa-jardin",
        "type": "villa",
        "label": "",
        "plan": "villa",
        "city": "Tunis",
        "neighborhood": "La Marsa",
        "title": "Villa avec jardin à l'année, La Marsa Cube",
        "description": (
            "Villa de 220 m² sur deux niveaux avec jardin arboré de 400 m², dans le quartier calme de "
            "La Marsa Cube. Trois chambres, deux salles de bain, double séjour avec cheminée, cuisine "
            "équipée, terrasse couverte.\n\n"
            "Garage pour deux voitures, chauffage central, climatisation. Proche du Lycée français et "
            "des plages ; louée meublée à l'année ou au mois (6 mois minimum)."
        ),
        "bedrooms": 3,
        "bathrooms": 2,
        "surface": 220,
        "floor": None,
        "elevator": False,
        "guests": 6,
        "grade": "good",
        "level": "verified",
        "monthly": 4200,
        "nightly": None,
        "yearly": 45600,
        "amenities": [
            "wifi",
            "ac",
            "heating",
            "kitchen",
            "water_heater",
            "washer",
            "dishwasher",
            "tv",
            "terrace",
            "garden",
            "parking",
            "intercom",
        ],
        "distances": {
            "Lycée français": "5 min en voiture",
            "Plage": "10 min en voiture",
            "TGM": "12 min à pied",
        },
        "charges_included": False,
        "charges": 200,
        "deposit": 2,
        "min_lease": 6,
        "rules": _RULES_PETS,
    },
    # ---------------------------------------------------------------- colocation
    {
        "key": "ghazela-coloc-chambre-1",
        "type": "room_in_shared_flat",
        "label": "",
        "plan": "room",
        "city": "Ariana",
        "neighborhood": "Ghazela",
        "title": "Chambre en colocation étudiante à 7 min d'ESPRIT",
        "description": (
            "Chambre privée de 14 m² dans un S+3 partagé par trois étudiants, à sept minutes à pied "
            "d'ESPRIT. Lit simple, bureau, armoire, fenêtre sur cour calme.\n\n"
            "Parties communes : séjour, cuisine équipée avec lave-linge, salle de bain. Fibre et "
            "charges incluses. Colocation non fumeur, ambiance studieuse."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 14,
        "floor": 2,
        "elevator": False,
        "guests": 1,
        "grade": "good",
        "level": "verified",
        "monthly": 350,
        "nightly": None,
        "yearly": 3900,
        "amenities": ["wifi", "kitchen", "water_heater", "washer", "desk"],
        "distances": {
            "ESPRIT": "7 min à pied",
            "Bus vers Tunis": "4 min à pied",
            "Épicerie": "2 min à pied",
        },
        "charges_included": True,
        "charges": 40,
        "deposit": 1,
        "min_lease": 6,
        "rules": _RULES,
    },
    {
        "key": "ghazela-coloc-chambre-2",
        "type": "room_in_shared_flat",
        "label": "",
        "plan": "room",
        "city": "Ariana",
        "neighborhood": "Ghazela",
        "title": "Grande chambre climatisée en colocation, Ghazela",
        "description": (
            "Chambre de 18 m² avec climatisation et balcon dans un appartement S+4 rénové, partagé "
            "par quatre étudiants ou jeunes actifs. Lit 140 cm, grand bureau, dressing.\n\n"
            "Cuisine équipée, deux salles de bain, salon commun avec télévision. Résidence avec "
            "ascenseur et gardien, à dix minutes à pied d'ESPRIT et du pôle technologique."
        ),
        "bedrooms": 1,
        "bathrooms": 2,
        "surface": 18,
        "floor": 3,
        "elevator": True,
        "guests": 1,
        "grade": "excellent",
        "level": "verified",
        "monthly": 400,
        "nightly": None,
        "yearly": None,
        "amenities": [
            "wifi",
            "ac",
            "kitchen",
            "water_heater",
            "washer",
            "tv",
            "desk",
            "balcony",
            "elevator",
            "security",
        ],
        "distances": {
            "ESPRIT": "10 min à pied",
            "Pôle technologique": "8 min à pied",
            "Supermarché": "5 min à pied",
        },
        "charges_included": True,
        "charges": 50,
        "deposit": 1,
        "min_lease": 3,
        "rules": _RULES,
    },
    {
        "key": "ghazela-coloc-chambre-3",
        "type": "room_in_shared_flat",
        "label": "",
        "plan": "room",
        "city": "Ariana",
        "neighborhood": "Ghazela",
        "title": "Chambre économique en colocation, cité Ghazela",
        "description": (
            "Chambre de 12 m² dans un S+3 partagé par trois étudiants, dans la cité Ghazela, à "
            "douze minutes à pied d'ESPRIT. Lit simple, bureau, étagères.\n\n"
            "Cuisine et salle de bain communes, machine à laver, Wi-Fi inclus. Mobilier simple, loyer "
            "très accessible, ambiance conviviale."
        ),
        "bedrooms": 1,
        "bathrooms": 1,
        "surface": 12,
        "floor": 1,
        "elevator": False,
        "guests": 1,
        "grade": "basic",
        "level": "verified",
        "monthly": 290,
        "nightly": None,
        "yearly": 3300,
        "amenities": ["wifi", "kitchen", "water_heater", "washer", "desk"],
        "distances": {"ESPRIT": "12 min à pied", "Bus": "3 min à pied", "Marché": "6 min à pied"},
        "charges_included": True,
        "charges": 30,
        "deposit": 1,
        "min_lease": 6,
        "rules": _RULES,
    },
]
