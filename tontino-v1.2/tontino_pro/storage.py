"""Persistance JSON locale de la tontine (hors-ligne)."""

import json
import os

from .config import DATA_FILE
from .models import Tontine


def load():
    """Charge la tontine depuis le fichier, ou renvoie une tontine vierge."""
    if not os.path.exists(DATA_FILE):
        return Tontine()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return Tontine.from_dict(data)
    except (json.JSONDecodeError, OSError):
        pass
    return Tontine()


def save(tontine):
    """Écrit la tontine sur le disque. Lève OSError en cas d'échec."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tontine.to_dict(), f, ensure_ascii=False, indent=2)
