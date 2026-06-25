"""Tontine ÉPARGNE (accumulation).

Pas de bénéficiaire à tour de rôle : à chaque séance, chacun dépose un montant
(libre). L'argent s'accumule dans un FONDS commun. À la fin du cycle, le fonds
est redistribué (à parts égales, ou au prorata de l'épargne de chacun).
"""

from .base import Engine
from ..models import Session
from ..utils import fmt_money


class EpargneEngine(Engine):
    type_id = "epargne"
    label = "Épargne (accumulation)"
    uses_penalties = False

    def current(self, t):
        return None

    def upcoming(self, t):
        return None

    def cards(self, t):
        nb_seances = sum(1 for s in t.historique if s.type == "epargne_depot")
        return {
            "primary": {"label": "🏦  FONDS ÉPARGNÉ", "value": fmt_money(t.fonds),
                        "sub": f"{nb_seances} séance(s) de collecte"},
            "secondary": {"label": "📤  DISTRIBUTION", "value": "en fin de cycle",
                          "sub": f"{len(t.membres)} membre(s) à servir"},
            "action": {"label": "💰  Encaisser une séance", "key": "epargne"},
            "extra": [{"label": "📤  Distribuer le fonds", "key": "distribute"}],
            "can_draw": False,
        }

    def stats(self, t):
        n = len(t.membres)
        moyenne = (t.fonds // n) if n else 0
        return [
            ("CYCLE · SÉANCE", f"Cycle {t.cycle} · Séance {t.tour}"),
            ("FONDS TOTAL", fmt_money(t.fonds)),
            ("MEMBRES", str(n)),
            ("MOYENNE / MEMBRE", fmt_money(moyenne)),
        ]

    def table_headers(self):
        return ("Épargne totale", "Dernier dépôt", "")

    def member_row(self, t, m):
        dernier = 0
        for s in reversed(t.historique):
            if s.type == "epargne_depot":
                for d in s.details:
                    if d.get("nom") == m.nom:
                        dernier = d.get("montant", 0)
                        break
                break
        return {"statut": fmt_money(m.epargne), "tag": "",
                "info1": fmt_money(dernier) if dernier else "—", "info2": ""}

    # --- Collecte d'une séance d'épargne ---
    def collect(self, t, depots, date):
        """depots : dict {nom_membre: montant}."""
        total = 0
        details = []
        for m in t.membres:
            montant = int(depots.get(m.nom, 0) or 0)
            if montant:
                m.epargne += montant
                total += montant
                details.append({"nom": m.nom, "montant": montant})
        t.fonds += total
        sess = Session(cycle=t.cycle, tour=t.tour, date=date, beneficiaire="(collecte épargne)",
                       montant=total, type="epargne_depot", details=details)
        t.historique.append(sess)
        t.tour += 1
        return sess

    # --- Distribution du fonds en fin de cycle ---
    def distribute(self, t, date, mode="egal"):
        if t.fonds <= 0 or not t.membres:
            return None
        n = len(t.membres)
        details = []
        if mode == "prorata":
            base = sum(m.epargne for m in t.membres) or 1
            for m in t.membres:
                part = round(t.fonds * m.epargne / base)
                details.append({"nom": m.nom, "montant": part})
        else:  # à parts égales
            part = t.fonds // n
            for m in t.membres:
                details.append({"nom": m.nom, "montant": part})
        sess = Session(cycle=t.cycle, tour=t.tour, date=date, beneficiaire="DISTRIBUTION",
                       montant=t.fonds, type="epargne_distrib", details=details)
        t.historique.append(sess)
        # Clôture du cycle d'épargne
        t.fonds = 0
        for m in t.membres:
            m.epargne = 0
        t.cycle += 1
        t.tour = 1
        return sess

    def new_cycle(self, t):
        # Pour l'épargne, un « nouveau cycle » repart à zéro (fonds + épargnes).
        t.fonds = 0
        for m in t.membres:
            m.epargne = 0
            m.recu = False
            m.date_recu = None
        t.tour = 1
        t.cycle += 1
