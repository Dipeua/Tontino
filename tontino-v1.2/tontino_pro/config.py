"""Constantes, valeurs par défaut, libellés et palette de couleurs."""

import os

APP_NAME = "Tontino-Pro"
APP_SUBTITLE = "Gestion de tontines"

# Le fichier de données est rangé à la racine du projet (à côté de run.py).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "tontine.json")

# --- Valeurs par défaut ---
COTISATION_DEFAUT = 30000

PENALITES_DEFAUT = {
    "absence": 1000,
    "retard_physique": 500,
    "retard_cotisation": 1000,
    "echec_cotisation": 5000,
}
PENALITES_LABELS = {
    "absence": "Absence",
    "retard_physique": "Retard physique",
    "retard_cotisation": "Retard cotisation",
    "echec_cotisation": "Échec cotisation",
}

# Types de tontine disponibles (id -> libellé lisible)
TYPES = {
    "rotative": "Rotative (tour de rôle)",
    "encheres": "À enchères (mises)",
    "epargne":  "Épargne (accumulation)",
}

# Ordre de passage (pour la rotative)
ORDRES = {
    "fixe":   "Ordre fixe",
    "tirage": "Tirage au sort",
}

# --- Palette d'accents (valables en clair et sombre) ---
BLUE,  BLUE_D  = "#2563eb", "#1d4ed8"
GREEN, GREEN_D = "#16a34a", "#15803d"
RED,   RED_D   = "#dc2626", "#b91c1c"
AMBER, AMBER_D = "#d97706", "#b45309"
SLATE, SLATE_D = "#475569", "#334155"
CYAN,  CYAN_D  = "#0891b2", "#0e7490"
VIOLET, VIOLET_D = "#7c3aed", "#6d28d9"

# Fonds des cartes vedettes (clair, sombre)
PRIMARY_BG   = ("#dcfce7", "#14532d")   # vert
SECONDARY_BG = ("#dbeafe", "#1e3a5f")   # bleu
