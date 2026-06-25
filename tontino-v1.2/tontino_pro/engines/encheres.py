"""Tontine À ENCHÈRES (mises).

À chaque séance, les membres « misent » : celui qui propose la plus grosse mise
remporte la cagnotte. La mise gagnante est versée à la caisse (puis partagée
selon les règles du groupe). Un membre ne peut gagner qu'une fois par cycle.
"""

from .base import Engine
from ..models import Session
from ..utils import fmt_money


class EncheresEngine(Engine):
    type_id = "encheres"
    label = "À enchères (mises)"
    uses_penalties = True

    def current(self, t):
        return None     # le bénéficiaire n'est pas prédéterminé : il est adjugé

    def upcoming(self, t):
        return None

    def _dernier_gagnant(self, t):
        for s in reversed(t.historique):
            if s.type == "encheres":
                return s
        return None

    def cards(self, t):
        cag = t.cagnotte()
        dernier = self._dernier_gagnant(t)
        restants = t.restants()
        if not restants:
            primary_val = "Cycle terminé 🎉" if t.membres else "— aucun membre —"
            sub = "lancez un nouveau cycle" if t.membres else ""
        else:
            primary_val, sub = "À adjuger", f"cagnotte {fmt_money(cag)} · {len(restants)} en lice"
        return {
            "primary": {"label": "🔨  ENCHÈRE EN COURS", "value": primary_val, "sub": sub},
            "secondary": {"label": "🏆  DERNIER GAGNANT",
                          "value": dernier.beneficiaire if dernier else "—",
                          "sub": (f"mise {fmt_money(dernier.mise)} · {dernier.date}"
                                  if dernier else "aucune enchère")},
            "action": {"label": "🔨  Adjuger l'enchère", "key": "enchere"},
            "extra": [],
            "can_draw": False,
        }

    def stats(self, t):
        n = len(t.membres)
        recu = sum(1 for m in t.membres if m.recu)
        total_mises = sum(s.mise for s in t.historique if s.type == "encheres")
        return [
            ("CYCLE · TOUR", f"Cycle {t.cycle} · Tour {t.tour}"),
            ("CAGNOTTE", fmt_money(t.cagnotte())),
            ("ONT GAGNÉ", f"{recu} / {n}" if n else "—"),
            ("CAISSE (MISES)", fmt_money(t.caisse)),
        ]

    def table_headers(self):
        return ("Statut", "Cotisation", "Pénalités")

    def member_row(self, t, m):
        if m.recu:
            statut = "🏆 A remporté" + (f" · {m.date_recu}" if m.date_recu else "")
            tag = "done"
        else:
            statut, tag = "En lice", ""
        pen = t.penalite_membre(m)
        return {"statut": statut, "tag": tag,
                "info1": "✓ Payé" if m.seance.get("cotise") else "—",
                "info2": fmt_money(pen) if pen else "—"}

    def validate(self, t, gagnant_nom, date, mise):
        b = next((m for m in t.restants() if m.nom == gagnant_nom), None)
        if b is None:
            return None
        cag = t.cagnotte()
        pen = t.penalites_seance()
        details = t.details_penalites()
        b.recu, b.date_recu = True, date
        t.caisse += pen + mise
        sess = Session(cycle=t.cycle, tour=t.tour, date=date, beneficiaire=b.nom,
                       montant=cag, penalites=pen, mise=mise, type="encheres", details=details)
        t.historique.append(sess)
        t.tour += 1
        t.reset_seances()
        return sess
