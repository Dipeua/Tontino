"""Registre des moteurs de tontine."""

from .rotative import RotativeEngine
from .encheres import EncheresEngine
from .epargne import EpargneEngine

_ENGINES = {
    "rotative": RotativeEngine(),
    "encheres": EncheresEngine(),
    "epargne":  EpargneEngine(),
}


def get_engine(type_id):
    """Renvoie le moteur correspondant au type (rotative par défaut)."""
    return _ENGINES.get(type_id, _ENGINES["rotative"])
