"""Modèle de données : Member, Session et Tontine (état complet).

Tout est sérialisable en/depuis des dictionnaires (pour le stockage JSON).
La classe Tontine ne contient QUE des données + des helpers neutres ;
la logique propre à chaque type de tontine vit dans les « moteurs » (engines).
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .config import COTISATION_DEFAUT, PENALITES_DEFAUT, PENALITES_LABELS


def seance_vierge():
    """Pointage d'un membre pour la séance en cours (remis à zéro à chaque tour)."""
    return {
        "presence": None,            # "present" | "absent" | None
        "cotise": False,
        "retard_physique": False,
        "retard_cotisation": False,
        "echec_cotisation": False,
    }


@dataclass
class Member:
    nom: str
    tel: str = ""
    recu: bool = False               # a déjà bénéficié (rotative / enchères)
    date_recu: Optional[str] = None
    epargne: int = 0                 # total épargné (mode épargne)
    seance: dict = field(default_factory=seance_vierge)

    def to_dict(self):
        return {
            "nom": self.nom, "tel": self.tel, "recu": self.recu,
            "date_recu": self.date_recu, "epargne": self.epargne, "seance": self.seance,
        }

    @classmethod
    def from_dict(cls, d):
        s = seance_vierge()
        sj = d.get("seance", {}) or {}
        if sj.get("presence") in ("present", "absent"):
            s["presence"] = sj["presence"]
        for k in ("cotise", "retard_physique", "retard_cotisation", "echec_cotisation"):
            s[k] = bool(sj.get(k, False))
        return cls(
            nom=str(d.get("nom", "")), tel=str(d.get("tel", "")),
            recu=bool(d.get("recu", False)), date_recu=d.get("date_recu"),
            epargne=int(d.get("epargne", 0) or 0), seance=s,
        )


@dataclass
class Session:
    """Une séance enregistrée dans l'historique (selon le type de tontine)."""
    cycle: int
    tour: int
    date: str
    beneficiaire: str
    montant: int = 0                 # cagnotte remise / total encaissé
    penalites: int = 0
    mise: int = 0                    # enchères : montant de la mise gagnante
    type: str = "rotative"
    details: list = field(default_factory=list)   # pénalités OU dépôts

    def to_dict(self):
        return {
            "cycle": self.cycle, "tour": self.tour, "date": self.date,
            "beneficiaire": self.beneficiaire, "montant": self.montant,
            "penalites": self.penalites, "mise": self.mise, "type": self.type,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            cycle=int(d.get("cycle", 1)), tour=int(d.get("tour", 1)),
            date=str(d.get("date", "")), beneficiaire=str(d.get("beneficiaire", "")),
            # rétro-compat : ancien champ "cagnotte"
            montant=int(d.get("montant", d.get("cagnotte", 0)) or 0),
            penalites=int(d.get("penalites", 0) or 0), mise=int(d.get("mise", 0) or 0),
            type=str(d.get("type", "rotative")), details=d.get("details", []) or [],
        )


@dataclass
class Tontine:
    nom: str = "Ma tontine"
    type: str = "rotative"           # rotative | encheres | epargne
    ordre: str = "fixe"              # fixe | tirage (rotative)
    cotisation: int = COTISATION_DEFAUT
    penalites: dict = field(default_factory=lambda: dict(PENALITES_DEFAUT))
    tour: int = 1
    cycle: int = 1
    caisse: int = 0                  # épargne issue des pénalités (non distribuée)
    fonds: int = 0                   # fonds accumulé (mode épargne)
    membres: List[Member] = field(default_factory=list)
    historique: List[Session] = field(default_factory=list)

    # --- Helpers neutres (utilisés par les moteurs) ---
    def restants(self):
        return [m for m in self.membres if not m.recu]

    def cagnotte(self):
        return self.cotisation * len(self.membres)

    def penalite_membre(self, m):
        s, p, t = m.seance, self.penalites, 0
        if s.get("presence") == "absent":
            t += p["absence"]
        if s.get("retard_physique"):
            t += p["retard_physique"]
        if s.get("retard_cotisation"):
            t += p["retard_cotisation"]
        if s.get("echec_cotisation"):
            t += p["echec_cotisation"]
        return t

    def penalites_seance(self):
        return sum(self.penalite_membre(m) for m in self.membres)

    def details_penalites(self):
        out = []
        for m in self.membres:
            s, motifs = m.seance, []
            if s.get("presence") == "absent":
                motifs.append(PENALITES_LABELS["absence"])
            if s.get("retard_physique"):
                motifs.append(PENALITES_LABELS["retard_physique"])
            if s.get("retard_cotisation"):
                motifs.append(PENALITES_LABELS["retard_cotisation"])
            if s.get("echec_cotisation"):
                motifs.append(PENALITES_LABELS["echec_cotisation"])
            montant = self.penalite_membre(m)
            if montant > 0:
                out.append({"nom": m.nom, "motifs": motifs, "montant": montant})
        return out

    def reset_seances(self):
        for m in self.membres:
            m.seance = seance_vierge()

    # --- Sérialisation ---
    def to_dict(self):
        return {
            "nom": self.nom, "type": self.type, "ordre": self.ordre,
            "cotisation": self.cotisation, "penalites": self.penalites,
            "tour": self.tour, "cycle": self.cycle, "caisse": self.caisse,
            "fonds": self.fonds,
            "membres": [m.to_dict() for m in self.membres],
            "historique": [s.to_dict() for s in self.historique],
        }

    @classmethod
    def from_dict(cls, d):
        def _int(v, dflt):
            try:
                return int(v)
            except (ValueError, TypeError):
                return dflt
        pen = dict(PENALITES_DEFAUT)
        for k in PENALITES_DEFAUT:
            pen[k] = _int((d.get("penalites") or {}).get(k, PENALITES_DEFAUT[k]),
                          PENALITES_DEFAUT[k])
        t = cls(
            nom=str(d.get("nom", "Ma tontine")),
            type=d.get("type", "rotative") if d.get("type") in ("rotative", "encheres", "epargne") else "rotative",
            ordre="tirage" if d.get("ordre") == "tirage" else "fixe",
            cotisation=_int(d.get("cotisation", COTISATION_DEFAUT), COTISATION_DEFAUT),
            penalites=pen,
            tour=max(1, _int(d.get("tour", 1), 1)),
            cycle=max(1, _int(d.get("cycle", 1), 1)),
            caisse=_int(d.get("caisse", 0), 0),
            fonds=_int(d.get("fonds", 0), 0),
        )
        for md in d.get("membres", []) or []:
            if md.get("nom"):
                t.membres.append(Member.from_dict(md))
        for sd in d.get("historique", []) or []:
            t.historique.append(Session.from_dict(sd))
        return t
