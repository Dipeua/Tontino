"""Petits utilitaires partagés."""

import re


def fmt_money(value):
    """1500000 -> '1 500 000 FCFA'."""
    try:
        return f"{int(value):,}".replace(",", " ") + " FCFA"
    except (ValueError, TypeError):
        return "0 FCFA"


def parse_int(text):
    """Extrait un entier d'une saisie libre ('30 000 F' -> 30000)."""
    digits = re.sub(r"\D", "", str(text))
    return int(digits) if digits else 0


def today():
    from datetime import datetime
    return datetime.now().strftime("%d/%m/%Y")
