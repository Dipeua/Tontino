"""Tontine ROTATIVE (njangi classique).

Cotisation fixe pour tous, un bénéficiaire par séance à tour de rôle.
Ordre « fixe » (liste) ou « tirage » au sort. Pénalités -> caisse.
"""

from .base import Engine
from ..models import Session
from ..utils import fmt_money


class RotativeEngine(Engine):
    type_id = "rotative"
    label = "Rotative (tour de rôle)"
    uses_penalties = True

    def can_draw(self, t):
        return t.ordre == "tirage"

    def cards(self, t):
        cur, nxt = self.current(t), self.upcoming(t)
        cag = t.cagnotte()
        if cur:
            primary_val, primary_sub = cur.nom, f"reçoit {fmt_money(cag)}"
        elif not t.membres:
            primary_val, primary_sub = "— aucun membre —", ""
        else:
            primary_val, primary_sub = "Cycle terminé 🎉", "lancez un nouveau cycle"
        return {
            "primary": {"label": "🍽  BOUFFE MAINTENANT", "value": primary_val, "sub": primary_sub},
            "secondary": {"label": "⏭  PROCHAIN À BOUFFER",
                          "value": nxt.nom if nxt else "—", "sub": "à la prochaine séance"},
            "action": {"label": "✓  Valider la séance", "key": "validate"},
            "extra": [],
            "can_draw": self.can_draw(t),
        }

    def stats(self, t):
        n = len(t.membres)
        recu = sum(1 for m in t.membres if m.recu)
        return [
            ("CYCLE · TOUR", f"Cycle {t.cycle} · Tour {t.tour}"),
            ("CAGNOTTE DU TOUR", fmt_money(t.cagnotte())),
            ("ONT BOUFFÉ", f"{recu} / {n}" if n else "—"),
            ("CAISSE (ÉPARGNE)", fmt_money(t.caisse)),
        ]

    def table_headers(self):
        return ("Statut", "Cotisation", "Pénalités")

    def member_row(self, t, m):
        cur, nxt = self.current(t), self.upcoming(t)
        if m.recu:
            statut = "✓ A bouffé" + (f" · {m.date_recu}" if m.date_recu else "")
            tag = "done"
        elif m is cur:
            statut, tag = "🍽 Bouffe maintenant", "cur"
        elif m is nxt:
            statut, tag = "⏭ Prochain", "next"
        else:
            statut, tag = "En attente", ""
        pen = t.penalite_membre(m)
        return {"statut": statut, "tag": tag,
                "info1": "✓ Payé" if m.seance.get("cotise") else "—",
                "info2": fmt_money(pen) if pen else "—"}

    # --- Validation d'une séance ---
    def validate(self, t, beneficiaire_nom, date):
        b = next((m for m in t.restants() if m.nom == beneficiaire_nom), None)
        if b is None:
            return None
        cag = t.cagnotte()
        pen = t.penalites_seance()
        details = t.details_penalites()
        b.recu, b.date_recu = True, date
        t.caisse += pen
        sess = Session(cycle=t.cycle, tour=t.tour, date=date, beneficiaire=b.nom,
                       montant=cag, penalites=pen, type="rotative", details=details)
        t.historique.append(sess)
        t.tour += 1
        t.reset_seances()
        return sess
