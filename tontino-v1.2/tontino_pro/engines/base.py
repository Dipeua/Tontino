"""Classe de base des moteurs de tontine (pattern Strategy).

Chaque type de tontine (rotative, enchères, épargne) hérite de Engine et
définit son comportement : qui bénéficie, ce qu'affichent les cartes, comment
valider une séance, etc. L'interface graphique ne connaît QUE cette interface,
elle ignore les détails de chaque type.
"""

from ..models import seance_vierge


class Engine:
    type_id = "base"
    label = "Base"
    uses_penalties = True            # le bouton « Pointer » est-il pertinent ?

    # --- Bénéficiaires (rotation) ---
    def current(self, t):
        """Membre qui bénéficie à cette séance (ou None)."""
        r = t.restants()
        return r[0] if r else None

    def upcoming(self, t):
        """Membre qui bénéficiera à la séance suivante (ou None)."""
        r = t.restants()
        return r[1] if len(r) > 1 else None

    # --- Tirage au sort (désactivé par défaut) ---
    def can_draw(self, t):
        return False

    def draw(self, t):
        import random
        idx = [i for i, m in enumerate(t.membres) if not m.recu]
        if len(idx) < 2:
            return False
        restants = [t.membres[i] for i in idx]
        random.shuffle(restants)
        for pos, i in enumerate(idx):
            t.membres[i] = restants[pos]
        return True

    # --- Affichage (à implémenter par les sous-classes) ---
    def cards(self, t):
        raise NotImplementedError

    def stats(self, t):
        raise NotImplementedError

    def table_headers(self):
        return ("Statut", "Cotisation", "Pénalités")

    def member_row(self, t, m):
        raise NotImplementedError

    # --- Cycle ---
    def new_cycle(self, t):
        for m in t.membres:
            m.recu = False
            m.date_recu = None
            m.seance = seance_vierge()
        t.tour = 1
        t.cycle += 1
