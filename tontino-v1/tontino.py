"""
Tontino — Gestion de tontine (njangi)
=====================================
Application de bureau 100 % locale (CustomTkinter), refondue autour d'une idée
simple : à tout moment on voit clairement QUI BOUFFE MAINTENANT et QUI SERA LE
PROCHAIN à la séance suivante.

Deux modes d'ordre de passage (Réglages)
-----------------------------------------
- « Ordre fixe »      : l'ordre des membres (modifiable avec ↑ ↓) décide qui bouffe.
- « Tirage au sort »  : un bouton 🎲 mélange au hasard l'ordre des membres qui
  n'ont pas encore bouffé (les bénéficiaires passés gardent leur place).

Dans les deux cas :
- « Bouffe maintenant » = le 1er membre qui n'a pas encore bouffé.
- « Prochain »          = le 2e membre qui n'a pas encore bouffé.
- Valider une séance fait bouffer le bénéficiaire choisi (par défaut celui qui
  « bouffe maintenant »), encaisse les pénalités dans la caisse, puis tout
  avance automatiquement.

Pénalités (alimentent la caisse d'épargne, non distribuée) :
  Absence · Retard physique · Retard cotisation · Échec cotisation.

Données : tontine.json (hors-ligne). Dépendances : customtkinter, reportlab.
Lancer :  python tontino.py
"""

import json
import os
import random
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

import customtkinter as ctk

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# --------------------------------------------------------------------------- #
APP_NAME = "Tontino"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tontine.json")

COTISATION_DEFAUT = 30000
PENALITES_DEFAUT = {
    "absence": 1000, "retard_physique": 500,
    "retard_cotisation": 1000, "echec_cotisation": 500,
}
PENALITES_LABELS = {
    "absence": "Absence", "retard_physique": "Retard physique",
    "retard_cotisation": "Retard cotisation", "echec_cotisation": "Échec cotisation",
}

# Accents
BLUE, BLUE_D   = "#2563eb", "#1d4ed8"
GREEN, GREEN_D = "#16a34a", "#15803d"
RED, RED_D     = "#dc2626", "#b91c1c"
AMBER, AMBER_D = "#d97706", "#b45309"
SLATE, SLATE_D = "#475569", "#334155"
CYAN, CYAN_D   = "#0891b2", "#0e7490"

# Fonds des cartes vedettes (clair, sombre)
CUR_BG  = ("#dcfce7", "#14532d")   # bouffe maintenant (vert)
NEXT_BG = ("#dbeafe", "#1e3a5f")   # prochain (bleu)


def fmt_money(v):
    try:
        return f"{int(v):,}".replace(",", " ") + " FCFA"
    except (ValueError, TypeError):
        return "0 FCFA"


def seance_vierge():
    return {"presence": None, "cotise": False, "retard_physique": False,
            "retard_cotisation": False, "echec_cotisation": False}


# --------------------------------------------------------------------------- #
class TontinoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_NAME} — Gestion de tontine")
        self.geometry("1060x800")
        self.minsize(940, 720)

        self.nom_tontine = "Ma tontine"
        self.cotisation = COTISATION_DEFAUT
        self.penalites = dict(PENALITES_DEFAUT)
        self.mode = "fixe"        # "fixe" (ordre de passage) ou "tirage" (au sort)
        self.tour = 1
        self.cycle = 1
        self.caisse = 0
        self.membres = []
        self.historique = []

        self._build_ui()
        self._load()
        self._refresh()
        self.bind("<Control-s>", lambda e: self._export_pdf())

    # ------------------------------ Logique ------------------------------- #
    def _restants(self):
        return [m for m in self.membres if not m["recu"]]

    def _courant(self):
        r = self._restants()
        return r[0] if r else None

    def _prochain(self):
        r = self._restants()
        return r[1] if len(r) > 1 else None

    def _penal_membre(self, m):
        s, p, t = m["seance"], self.penalites, 0
        if s.get("presence") == "absent":
            t += p["absence"]
        if s.get("retard_physique"):
            t += p["retard_physique"]
        if s.get("retard_cotisation"):
            t += p["retard_cotisation"]
        if s.get("echec_cotisation"):
            t += p["echec_cotisation"]
        return t

    def _penal_tour(self):
        return sum(self._penal_membre(m) for m in self.membres)

    def _details_penalites(self):
        out = []
        for m in self.membres:
            s, motifs = m["seance"], []
            if s.get("presence") == "absent":
                motifs.append(PENALITES_LABELS["absence"])
            if s.get("retard_physique"):
                motifs.append(PENALITES_LABELS["retard_physique"])
            if s.get("retard_cotisation"):
                motifs.append(PENALITES_LABELS["retard_cotisation"])
            if s.get("echec_cotisation"):
                motifs.append(PENALITES_LABELS["echec_cotisation"])
            mt = self._penal_membre(m)
            if mt > 0:
                out.append({"nom": m["nom"], "motifs": motifs, "montant": mt})
        return out

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except (ValueError, IndexError):
            return None

    # ------------------------------ UI ------------------------------------ #
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # --- Barre supérieure ---
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 4))
        top.grid_columnconfigure(0, weight=1)
        tb = ctk.CTkFrame(top, fg_color="transparent")
        tb.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(tb, text="🤝  " + APP_NAME,
                     font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        self.sub_lbl = ctk.CTkLabel(tb, text="", text_color=("gray40", "gray70"),
                                    font=ctk.CTkFont(size=12))
        self.sub_lbl.pack(anchor="w")
        rb = ctk.CTkFrame(top, fg_color="transparent")
        rb.grid(row=0, column=1, sticky="e")
        self.mode_sw = ctk.CTkSegmentedButton(rb, values=["☀", "🌙"],
                                              command=self._toggle_mode, width=80)
        self.mode_sw.set("☀")
        self.mode_sw.pack(side="left", padx=(0, 10))
        ctk.CTkButton(rb, text="⚙  Réglages", command=self._parametres,
                      fg_color=SLATE, hover_color=SLATE_D, width=120).pack(side="left")

        # --- Cartes vedettes : maintenant / prochain ---
        spot = ctk.CTkFrame(self, fg_color="transparent")
        spot.grid(row=1, column=0, sticky="ew", padx=22, pady=8)
        spot.grid_columnconfigure((0, 1), weight=1)

        cur = ctk.CTkFrame(spot, fg_color=CUR_BG, corner_radius=16)
        cur.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(cur, text="🍽  BOUFFE MAINTENANT",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=(GREEN_D, "#86efac")).pack(anchor="w", padx=18, pady=(14, 0))
        self.cur_name = ctk.CTkLabel(cur, text="—", font=ctk.CTkFont(size=24, weight="bold"),
                                     text_color=(GREEN_D, "#dcfce7"))
        self.cur_name.pack(anchor="w", padx=18)
        self.cur_sub = ctk.CTkLabel(cur, text="", text_color=(GREEN_D, "#bbf7d0"),
                                    font=ctk.CTkFont(size=12))
        self.cur_sub.pack(anchor="w", padx=18, pady=(0, 8))
        cur_btns = ctk.CTkFrame(cur, fg_color="transparent")
        cur_btns.pack(anchor="w", padx=18, pady=(0, 16), fill="x")
        ctk.CTkButton(cur_btns, text="✓  Valider la séance",
                      command=self._valider_seance, fg_color=GREEN, hover_color=GREEN_D,
                      height=36).pack(side="left")
        self.btn_tirage = ctk.CTkButton(cur_btns, text="🎲  Tirer au sort",
                                        command=self._tirer, fg_color=AMBER,
                                        hover_color=AMBER_D, height=36)
        # affiché seulement en mode tirage (géré dans _refresh)

        nxt = ctk.CTkFrame(spot, fg_color=NEXT_BG, corner_radius=16)
        nxt.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(nxt, text="⏭  PROCHAIN À BOUFFER",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=(BLUE_D, "#93c5fd")).pack(anchor="w", padx=18, pady=(14, 0))
        self.next_name = ctk.CTkLabel(nxt, text="—", font=ctk.CTkFont(size=22, weight="bold"),
                                      text_color=(BLUE_D, "#dbeafe"))
        self.next_name.pack(anchor="w", padx=18)
        self.next_sub = ctk.CTkLabel(nxt, text="à la prochaine séance",
                                     text_color=(BLUE_D, "#bfdbfe"), font=ctk.CTkFont(size=12))
        self.next_sub.pack(anchor="w", padx=18, pady=(0, 56))

        # --- Bandeau de stats ---
        stats = ctk.CTkFrame(self, corner_radius=12)
        stats.grid(row=2, column=0, sticky="ew", padx=22, pady=(2, 8))
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1)
        self.s_tour = self._chip(stats, 0, "CYCLE · TOUR", ("gray10", "gray90"))
        self.s_pot = self._chip(stats, 1, "CAGNOTTE DU TOUR", ("gray10", "gray90"))
        self.s_prog = self._chip(stats, 2, "ONT BOUFFÉ", ("gray10", "gray90"))
        self.s_caisse = self._chip(stats, 3, "CAISSE (ÉPARGNE)", AMBER)

        # --- Ajout de membre ---
        form = ctk.CTkFrame(self, corner_radius=12)
        form.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 8))
        form.grid_columnconfigure(0, weight=2)
        form.grid_columnconfigure(1, weight=1)
        self.nom_var, self.tel_var = tk.StringVar(), tk.StringVar()
        self.nom_entry = ctk.CTkEntry(form, textvariable=self.nom_var,
                                      placeholder_text="Nom du membre", height=38)
        self.nom_entry.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=14)
        self.tel_entry = ctk.CTkEntry(form, textvariable=self.tel_var,
                                      placeholder_text="Téléphone (optionnel)", height=38)
        self.tel_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=14)
        ctk.CTkButton(form, text="＋  Ajouter", command=self._add_membre,
                      height=38, width=130).grid(row=0, column=2, padx=(0, 14), pady=14)
        self.nom_entry.bind("<Return>", lambda e: self._add_membre())
        self.tel_entry.bind("<Return>", lambda e: self._add_membre())

        # --- Actions + tableau ---
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=4, column=0, sticky="nsew", padx=22, pady=(0, 6))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        acts = ctk.CTkFrame(body, fg_color="transparent")
        acts.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(acts, text="📝  Pointer", command=self._pointage,
                      fg_color=GREEN, hover_color=GREEN_D, width=110).pack(side="left")
        ctk.CTkButton(acts, text="✏  Modifier", command=self._edit_membre,
                      fg_color=CYAN, hover_color=CYAN_D, width=100).pack(side="left", padx=(8, 0))
        ctk.CTkButton(acts, text="↑", command=self._up, fg_color=SLATE,
                      hover_color=SLATE_D, width=40).pack(side="left", padx=(8, 0))
        ctk.CTkButton(acts, text="↓", command=self._down, fg_color=SLATE,
                      hover_color=SLATE_D, width=40).pack(side="left", padx=(6, 0))
        ctk.CTkButton(acts, text="🗑  Retirer", command=self._del_membre,
                      fg_color=RED, hover_color=RED_D, width=100).pack(side="left", padx=(8, 0))
        ctk.CTkButton(acts, text="📜  Historique", command=self._historique,
                      fg_color=SLATE, hover_color=SLATE_D, width=120).pack(side="right")
        ctk.CTkButton(acts, text="⬇  PDF", command=self._export_pdf,
                      fg_color="#0ea5e9", hover_color="#0284c7", width=80).pack(side="right", padx=(0, 8))
        ctk.CTkButton(acts, text="🔄  Nouveau cycle", command=self._nouveau_cycle,
                      fg_color=AMBER, hover_color=AMBER_D, width=150).pack(side="right", padx=(0, 8))

        wrap = ctk.CTkFrame(body, corner_radius=12)
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        self.style = ttk.Style()
        cols = ("ordre", "nom", "tel", "statut", "cotise", "penal")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        for c, t, w, a, st in (
                ("ordre", "#", 44, "center", False), ("nom", "Membre", 210, "w", True),
                ("tel", "Téléphone", 130, "w", False), ("statut", "Statut", 200, "w", False),
                ("cotise", "Cotisation", 95, "center", False), ("penal", "Pénalités", 100, "e", False)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=a, stretch=st)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=8, padx=(0, 8))
        self.tree.bind("<Double-1>", lambda e: self._pointage())
        self.tree.bind("<Delete>", lambda e: self._del_membre())
        self._style_tree()

        self.status = ctk.CTkLabel(self, text="Prêt.", anchor="w",
                                   text_color=("gray40", "gray70"), font=ctk.CTkFont(size=12))
        self.status.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 10))

    def _chip(self, parent, col, label, accent):
        c = ctk.CTkFrame(parent, fg_color="transparent")
        c.grid(row=0, column=col, sticky="ew", padx=14, pady=12)
        ctk.CTkLabel(c, text=label, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=("gray45", "gray60")).pack(anchor="w")
        v = ctk.CTkLabel(c, text="—", font=ctk.CTkFont(size=16, weight="bold"), text_color=accent)
        v.pack(anchor="w")
        return v

    def _style_tree(self):
        dark = ctk.get_appearance_mode() == "Dark"
        if dark:
            bg, fg, head = "#2b2b2b", "#dce4ee", "#212121"
            odd, even = "#2b2b2b", "#333333"
            cur_bg, next_bg, done_fg, done_bg = "#14532d", "#1e3a5f", "#7f8c9b", "#242424"
        else:
            bg, fg, head = "#ffffff", "#1e293b", "#eef2f7"
            odd, even = "#ffffff", "#f5f8fc"
            cur_bg, next_bg, done_fg, done_bg = "#dcfce7", "#dbeafe", "#94a3b8", "#eef1f5"
        s = self.style
        s.theme_use("clam")
        s.configure("Treeview", background=bg, fieldbackground=bg, foreground=fg,
                    rowheight=36, borderwidth=0, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", background=head,
                    foreground=("#94a3b8" if dark else "#64748b"),
                    font=("Segoe UI Semibold", 10), relief="flat", padding=8)
        s.map("Treeview.Heading", background=[("active", head)])
        s.map("Treeview", background=[("selected", BLUE)], foreground=[("selected", "#ffffff")])
        self.tree.tag_configure("odd", background=odd, foreground=fg)
        self.tree.tag_configure("even", background=even, foreground=fg)
        self.tree.tag_configure("cur", background=cur_bg)
        self.tree.tag_configure("next", background=next_bg)
        self.tree.tag_configure("done", foreground=done_fg, background=done_bg)

    def _toggle_mode(self, v):
        ctk.set_appearance_mode("dark" if v == "🌙" else "light")
        self._style_tree()
        self._refresh()

    def _status(self, msg, color=None):
        self.status.configure(text=msg, text_color=color or ("gray40", "gray70"))

    # ------------------------------ Membres ------------------------------- #
    def _add_membre(self):
        nom = self.nom_var.get().strip()
        if not nom:
            messagebox.showwarning("Champ manquant", "Entrez le nom du membre.")
            return
        if any(m["nom"].lower() == nom.lower() for m in self.membres):
            if not messagebox.askyesno("Doublon", f"« {nom} » existe déjà. L'ajouter quand même ?"):
                return
        self.membres.append({"nom": nom, "tel": self.tel_var.get().strip(),
                             "recu": False, "date_recu": None, "seance": seance_vierge()})
        self.nom_var.set("")
        self.tel_var.set("")
        self.nom_entry.focus_set()
        self._save()
        self._refresh()
        self._status(f"« {nom} » ajouté.", GREEN)

    def _del_membre(self):
        i = self._selected()
        if i is None:
            self._status("Sélectionnez un membre.", RED)
            return
        m = self.membres[i]
        if messagebox.askyesno("Retirer", f"Retirer « {m['nom']} » de la tontine ?"):
            self.membres.pop(i)
            self._save()
            self._refresh()
            self._status(f"« {m['nom']} » retiré.", RED)

    def _up(self):
        i = self._selected()
        if i and i > 0:
            self.membres[i - 1], self.membres[i] = self.membres[i], self.membres[i - 1]
            self._save()
            self._refresh()
            self.tree.selection_set(str(i - 1))

    def _down(self):
        i = self._selected()
        if i is not None and i < len(self.membres) - 1:
            self.membres[i + 1], self.membres[i] = self.membres[i], self.membres[i + 1]
            self._save()
            self._refresh()
            self.tree.selection_set(str(i + 1))

    def _edit_membre(self):
        i = self._selected()
        if i is None:
            self._status("Sélectionnez un membre.", RED)
            return
        m = self.membres[i]
        dlg, f = self._dialog("Modifier le membre", 430, 270)
        ctk.CTkLabel(f, text="✏  Modifier", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", pady=(0, 14))
        nv, tv = tk.StringVar(value=m["nom"]), tk.StringVar(value=m.get("tel", ""))
        ctk.CTkLabel(f, text="Nom", text_color=("gray40", "gray70")).pack(anchor="w")
        e = ctk.CTkEntry(f, textvariable=nv, height=38)
        e.pack(fill="x", pady=(2, 12))
        ctk.CTkLabel(f, text="Téléphone", text_color=("gray40", "gray70")).pack(anchor="w")
        ctk.CTkEntry(f, textvariable=tv, height=38).pack(fill="x", pady=(2, 16))

        def ok():
            nom = nv.get().strip()
            if not nom:
                messagebox.showwarning("Champ manquant", "Le nom est vide.", parent=dlg)
                return
            m["nom"], m["tel"] = nom, tv.get().strip()
            self._save()
            self._refresh()
            self._status(f"« {nom} » modifié.", GREEN)
            dlg.destroy()
        self._dialog_buttons(f, dlg, ok, "✓  Enregistrer")
        e.focus_set()
        dlg.bind("<Return>", lambda ev: ok())

    # ------------------------------ Pointage ------------------------------ #
    def _pointage(self):
        i = self._selected()
        if i is None:
            self._status("Sélectionnez un membre à pointer.", RED)
            return
        m = self.membres[i]
        s = m["seance"]
        dlg, f = self._dialog(f"Pointage — {m['nom']}", 460, 460)
        ctk.CTkLabel(f, text=f"📝  Pointage · Tour {self.tour}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(f, text=m["nom"], text_color=("gray40", "gray70")).pack(anchor="w", pady=(0, 12))
        pres = tk.StringVar(value=s.get("presence") or "present")
        cot = tk.BooleanVar(value=s.get("cotise", False))
        rp = tk.BooleanVar(value=s.get("retard_physique", False))
        rc = tk.BooleanVar(value=s.get("retard_cotisation", False))
        ec = tk.BooleanVar(value=s.get("echec_cotisation", False))
        tot = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color=AMBER)

        def recompute(*_):
            p, t = self.penalites, 0
            if pres.get() == "absent":
                t += p["absence"]
            if rp.get():
                t += p["retard_physique"]
            if rc.get():
                t += p["retard_cotisation"]
            if ec.get():
                t += p["echec_cotisation"]
            tot.configure(text=f"Pénalités → caisse : {fmt_money(t)}")

        pr = ctk.CTkFrame(f, fg_color="transparent")
        pr.pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(pr, text="Présence :").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(pr, text="Présent", variable=pres, value="present",
                           command=recompute).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(pr, text=f"Absent (+{self.penalites['absence']})", variable=pres,
                           value="absent", command=recompute).pack(side="left")
        ctk.CTkCheckBox(f, text=f"A payé sa cotisation ({fmt_money(self.cotisation)})",
                        variable=cot, command=recompute).pack(anchor="w", pady=(8, 4))
        ctk.CTkLabel(f, text="Pénalités :", text_color=("gray40", "gray70")).pack(anchor="w", pady=(8, 2))
        ctk.CTkCheckBox(f, text=f"Retard physique (+{self.penalites['retard_physique']})",
                        variable=rp, command=recompute).pack(anchor="w", pady=4)
        ctk.CTkCheckBox(f, text=f"Retard cotisation (+{self.penalites['retard_cotisation']})",
                        variable=rc, command=recompute).pack(anchor="w", pady=4)
        ctk.CTkCheckBox(f, text=f"Échec cotisation (+{self.penalites['echec_cotisation']})",
                        variable=ec, command=recompute).pack(anchor="w", pady=4)
        tot.pack(anchor="w", pady=(14, 12))
        recompute()

        def ok():
            s.update(presence=pres.get(), cotise=cot.get(), retard_physique=rp.get(),
                     retard_cotisation=rc.get(), echec_cotisation=ec.get())
            self._save()
            self._refresh()
            if str(i) in self.tree.get_children():
                self.tree.selection_set(str(i))
            self._status(f"Pointage de « {m['nom']} » enregistré.", GREEN)
            dlg.destroy()
        self._dialog_buttons(f, dlg, ok, "✓  Enregistrer")

    # ------------------------ Valider une séance -------------------------- #
    def _valider_seance(self):
        restants = self._restants()
        if not restants:
            if self.membres:
                messagebox.showinfo("Cycle terminé",
                                    "Tout le monde a bouffé. Lancez un « Nouveau cycle ».")
            else:
                messagebox.showinfo("Aucun membre", "Ajoutez d'abord des membres.")
            return
        defaut = self._courant()
        cagnotte = self.cotisation * len(self.membres)
        pen = self._penal_tour()
        dlg, f = self._dialog("Valider la séance", 480, 430)
        ctk.CTkLabel(f, text=f"✓  Valider la séance · Tour {self.tour}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 12))
        ctk.CTkLabel(f, text="🍽  Qui bouffe (reçoit la cagnotte) ?",
                     text_color=("gray40", "gray70")).pack(anchor="w")
        bvar = tk.StringVar(value=defaut["nom"])
        ctk.CTkOptionMenu(f, variable=bvar, values=[m["nom"] for m in restants]).pack(
            fill="x", pady=(2, 12))
        info = (f"💰  Cagnotte remise : {fmt_money(cagnotte)}\n"
                f"🏦  Pénalités → caisse : {fmt_money(pen)}\n"
                f"📦  Caisse après séance : {fmt_money(self.caisse + pen)}")
        ctk.CTkLabel(f, text=info, justify="left", anchor="w").pack(anchor="w", fill="x")
        non_cot = [m for m in self.membres if not m["seance"]["cotise"]]
        if non_cot:
            ctk.CTkLabel(f, text=f"⚠ {len(non_cot)} membre(s) sans cotisation cochée.",
                         text_color=RED).pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(f, text="Date de la séance", text_color=("gray40", "gray70")).pack(
            anchor="w", pady=(12, 2))
        dvar = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        ctk.CTkEntry(f, textvariable=dvar, width=170, height=36).pack(anchor="w")

        def ok():
            b = next((m for m in restants if m["nom"] == bvar.get()), None)
            if b is None:
                return
            date = dvar.get().strip() or datetime.now().strftime("%d/%m/%Y")
            b["recu"], b["date_recu"] = True, date
            self.caisse += pen
            self.historique.append({
                "cycle": self.cycle, "tour": self.tour, "date": date,
                "beneficiaire": b["nom"], "cagnotte": cagnotte, "penalites": pen,
                "details": self._details_penalites()})
            self.tour += 1
            for m in self.membres:
                m["seance"] = seance_vierge()
            self._save()
            self._refresh()
            self._status(f"{b['nom']} a bouffé {fmt_money(cagnotte)} le {date}.", GREEN)
            dlg.destroy()
            if not self._restants():
                messagebox.showinfo("Cycle terminé 🎉",
                                    "Tout le monde a bouffé une fois !\nLancez un « Nouveau cycle ».")
        self._dialog_buttons(f, dlg, ok, "✓  Valider", GREEN, GREEN_D)

    def _tirer(self):
        """Tire au sort l'ordre de passage des membres qui n'ont pas encore bouffé."""
        idx = [i for i, m in enumerate(self.membres) if not m["recu"]]
        if len(idx) < 2:
            self._status("Pas assez de membres à tirer au sort.", AMBER)
            return
        if not messagebox.askyesno(
                "Tirage au sort",
                "Tirer au sort l'ordre de passage des membres qui n'ont pas encore bouffé ?\n\n"
                "« Bouffe maintenant » et « Prochain » seront redéfinis au hasard."):
            return
        restants = [self.membres[i] for i in idx]
        random.shuffle(restants)
        for pos, i in enumerate(idx):
            self.membres[i] = restants[pos]
        self._save()
        self._refresh()
        cur = self._courant()
        self._status(f"🎲 Tirage effectué — {cur['nom']} bouffe cette séance." if cur
                     else "Tirage effectué.", GREEN)

    def _nouveau_cycle(self):
        if not self.membres:
            return
        if not messagebox.askyesno(
                "Nouveau cycle",
                "Démarrer un nouveau cycle ?\n\nTout le monde repasse à « n'a pas encore bouffé », "
                "le pointage est remis à zéro, retour au tour 1.\n\n"
                "La caisse et l'historique sont CONSERVÉS."):
            return
        for m in self.membres:
            m["recu"], m["date_recu"], m["seance"] = False, None, seance_vierge()
        self.tour, self.cycle = 1, self.cycle + 1
        self._save()
        self._refresh()
        self._status(f"Cycle {self.cycle} démarré.", GREEN)

    # ------------------------------ Dialogues helpers --------------------- #
    def _dialog(self, title, w, h):
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.transient(self)
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        dlg.after(120, dlg.grab_set)
        dlg.after(10, dlg.lift)
        f = ctk.CTkFrame(dlg, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=22, pady=22)
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        return dlg, f

    def _dialog_buttons(self, frame, dlg, ok_cmd, ok_text, color=BLUE, hover=BLUE_D):
        b = ctk.CTkFrame(frame, fg_color="transparent")
        b.pack(fill="x", side="bottom", pady=(14, 0))
        ctk.CTkButton(b, text="Annuler", command=dlg.destroy, fg_color=SLATE,
                      hover_color=SLATE_D, width=100).pack(side="right", padx=(8, 0))
        ctk.CTkButton(b, text=ok_text, command=ok_cmd, fg_color=color,
                      hover_color=hover, width=140).pack(side="right")

    def _parametres(self):
        dlg, f = self._dialog("Réglages de la tontine", 460, 560)
        ctk.CTkLabel(f, text="⚙  Réglages", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", pady=(0, 14))
        nv = tk.StringVar(value=self.nom_tontine)
        cv = tk.StringVar(value=str(self.cotisation))
        ctk.CTkLabel(f, text="Nom de la tontine", text_color=("gray40", "gray70")).pack(anchor="w")
        ctk.CTkEntry(f, textvariable=nv, height=36).pack(fill="x", pady=(2, 10))
        ctk.CTkLabel(f, text="Cotisation par membre / séance (FCFA)",
                     text_color=("gray40", "gray70")).pack(anchor="w")
        ctk.CTkEntry(f, textvariable=cv, height=36).pack(fill="x", pady=(2, 12))

        ctk.CTkLabel(f, text="Ordre de passage (qui bouffe)",
                     text_color=("gray40", "gray70")).pack(anchor="w")
        mode_seg = ctk.CTkSegmentedButton(f, values=["Ordre fixe", "Tirage au sort"])
        mode_seg.set("Tirage au sort" if self.mode == "tirage" else "Ordre fixe")
        mode_seg.pack(fill="x", pady=(2, 12))
        ctk.CTkLabel(f, text="Pénalités (→ caisse)",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(2, 6))
        pv = {}
        for k in ("absence", "retard_physique", "retard_cotisation", "echec_cotisation"):
            row = ctk.CTkFrame(f, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=PENALITES_LABELS[k]).pack(side="left")
            v = tk.StringVar(value=str(self.penalites[k]))
            pv[k] = v
            ctk.CTkEntry(row, textvariable=v, width=120, height=32).pack(side="right")

        def to_int(x):
            d = re.sub(r"\D", "", x)
            return int(d) if d else 0

        def ok():
            self.nom_tontine = nv.get().strip() or "Ma tontine"
            self.cotisation = to_int(cv.get())
            self.mode = "tirage" if mode_seg.get() == "Tirage au sort" else "fixe"
            for k, v in pv.items():
                self.penalites[k] = to_int(v.get())
            self._save()
            self._refresh()
            self._status("Réglages enregistrés.", GREEN)
            dlg.destroy()
        self._dialog_buttons(f, dlg, ok, "✓  Enregistrer")

    # ------------------------------ Historique ---------------------------- #
    def _historique(self):
        dlg, f = self._dialog("Historique des séances", 760, 560)
        ctk.CTkLabel(f, text="📜  Historique des séances",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        self.h_info = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13, weight="bold"),
                                   text_color=AMBER)
        self.h_info.pack(anchor="w", pady=(2, 8))
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(bar, text="➕  Ajouter une séance passée",
                      command=lambda: self._add_passe(dlg), fg_color=GREEN,
                      hover_color=GREEN_D, width=220).pack(side="left")
        ctk.CTkLabel(bar, text="  (pour saisir votre cahier, dans l'ordre)",
                     text_color=("gray40", "gray70")).pack(side="left")
        content = ctk.CTkScrollableFrame(f, label_text="")
        content.pack(fill="both", expand=True, pady=(0, 12))

        def build():
            for w in content.winfo_children():
                w.destroy()
            self.h_info.configure(text=f"Caisse : {fmt_money(self.caisse)}    ·    "
                                       f"Cycle {self.cycle} · Tour {self.tour}")
            if not self.historique:
                ctk.CTkLabel(content, text="Aucune séance enregistrée.",
                             text_color=("gray40", "gray70")).pack(anchor="w", pady=18)
                return
            head = ctk.CTkFrame(content, fg_color=("gray85", "gray25"))
            head.pack(fill="x", pady=(0, 2))
            for t, w in (("Cycle", 50), ("Tour", 45), ("Date", 90), ("A bouffé", 170),
                         ("Cagnotte", 105), ("Pénal.", 90), ("", 40)):
                ctk.CTkLabel(head, text=t, width=w, font=ctk.CTkFont(weight="bold"),
                             anchor="w").pack(side="left", padx=5, pady=4)
            for idx, h in enumerate(self.historique):
                row = ctk.CTkFrame(content, fg_color="transparent")
                row.pack(fill="x")
                for t, w in ((str(h.get("cycle", 1)), 50), (str(h["tour"]), 45),
                             (h.get("date", ""), 90), (h["beneficiaire"], 170),
                             (fmt_money(h["cagnotte"]), 105), (fmt_money(h["penalites"]), 90)):
                    ctk.CTkLabel(row, text=t, width=w, anchor="w").pack(side="left", padx=5, pady=2)
                ctk.CTkButton(row, text="🗑", width=34, fg_color=RED, hover_color=RED_D,
                              command=lambda i=idx: self._del_hist(i, build)).pack(side="left", padx=5)
                for d in h.get("details", []):
                    ctk.CTkLabel(content,
                                 text=f"        ⤷ {d['nom']} : {', '.join(d['motifs'])}  —  {fmt_money(d['montant'])}",
                                 anchor="w", font=ctk.CTkFont(size=11),
                                 text_color=("gray45", "gray60")).pack(fill="x", padx=10)
        self._h_build = build
        build()
        ctk.CTkButton(f, text="Fermer", command=dlg.destroy, width=110).pack(anchor="e")

    def _add_passe(self, parent):
        restants = self._restants()
        if not restants:
            messagebox.showinfo("Complet", "Tout le monde a déjà bouffé dans ce cycle.", parent=parent)
            return
        dlg, f = self._dialog("Ajouter une séance passée", 540, 640)
        ctk.CTkLabel(f, text="➕  Séance passée (cahier)",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(f, text=f"Sera enregistrée comme Cycle {self.cycle} · Tour {self.tour}.",
                     text_color=("gray40", "gray70")).pack(anchor="w", pady=(0, 10))
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x")
        top.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(top, text="Qui a bouffé ?", text_color=("gray40", "gray70")).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(top, text="Date (jj/mm/aaaa)", text_color=("gray40", "gray70")).grid(
            row=0, column=1, sticky="w", padx=(8, 0))
        bvar = tk.StringVar(value=restants[0]["nom"])
        ctk.CTkOptionMenu(top, variable=bvar, values=[m["nom"] for m in restants]).grid(
            row=1, column=0, sticky="ew", pady=(2, 10))
        dvar = tk.StringVar()
        de = ctk.CTkEntry(top, textvariable=dvar, height=34, placeholder_text="ex. 15/03/2026")
        de.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 10))
        ctk.CTkLabel(f, text="Cagnotte remise (FCFA)", text_color=("gray40", "gray70")).pack(anchor="w")
        cvar = tk.StringVar(value=str(self.cotisation * len(self.membres)))
        ctk.CTkEntry(f, textvariable=cvar, height=34).pack(fill="x", pady=(2, 12))
        ctk.CTkLabel(f, text="Pénalités (qui, pourquoi)",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(2, 4))
        motifs = [PENALITES_LABELS[k] for k in
                  ("absence", "retard_physique", "retard_cotisation", "echec_cotisation")]
        l2k = {PENALITES_LABELS[k]: k for k in PENALITES_DEFAUT}
        ar = ctk.CTkFrame(f, fg_color="transparent")
        ar.pack(fill="x")
        ar.grid_columnconfigure((0, 1), weight=2)
        mvar = tk.StringVar(value=self.membres[0]["nom"])
        movar = tk.StringVar(value=motifs[0])
        ctk.CTkOptionMenu(ar, variable=mvar, values=[m["nom"] for m in self.membres]).grid(
            row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkOptionMenu(ar, variable=movar, values=motifs).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        lignes = []
        box = ctk.CTkScrollableFrame(f, label_text="", height=130)
        box.pack(fill="x", pady=(8, 6))
        tot = ctk.CTkLabel(f, text="Total : 0 FCFA", font=ctk.CTkFont(weight="bold"), text_color=AMBER)
        tot.pack(anchor="w", pady=(0, 10))

        def refresh_lignes():
            for w in box.winfo_children():
                w.destroy()
            total = 0
            for i, lg in enumerate(lignes):
                total += lg["montant"]
                r = ctk.CTkFrame(box, fg_color="transparent")
                r.pack(fill="x", pady=1)
                ctk.CTkLabel(r, text=f"{lg['nom']} — {lg['motif']} : {fmt_money(lg['montant'])}",
                             anchor="w").pack(side="left")
                ctk.CTkButton(r, text="✕", width=28, fg_color=RED, hover_color=RED_D,
                              command=lambda x=i: (lignes.pop(x), refresh_lignes())).pack(side="right")
            tot.configure(text=f"Total pénalités → caisse : {fmt_money(total)}")

        def add_l():
            lignes.append({"nom": mvar.get(), "motif": movar.get(),
                           "montant": self.penalites[l2k[movar.get()]]})
            refresh_lignes()
        ctk.CTkButton(ar, text="➕", width=44, command=add_l).grid(row=0, column=2)

        def to_int(x):
            d = re.sub(r"\D", "", x)
            return int(d) if d else 0

        def ok():
            b = next((m for m in restants if m["nom"] == bvar.get()), None)
            if b is None:
                return
            date = dvar.get().strip()
            if not date and not messagebox.askyesno("Date vide", "Continuer sans date ?", parent=dlg):
                return
            par = {}
            for lg in lignes:
                d = par.setdefault(lg["nom"], {"nom": lg["nom"], "motifs": [], "montant": 0})
                d["motifs"].append(lg["motif"])
                d["montant"] += lg["montant"]
            pen = sum(lg["montant"] for lg in lignes)
            b["recu"], b["date_recu"] = True, date or None
            self.caisse += pen
            self.historique.append({"cycle": self.cycle, "tour": self.tour, "date": date,
                                    "beneficiaire": b["nom"], "cagnotte": to_int(cvar.get()),
                                    "penalites": pen, "details": list(par.values())})
            self.tour += 1
            self._save()
            self._refresh()
            self._status(f"Séance passée : {b['nom']} a bouffé.", GREEN)
            dlg.destroy()
            if getattr(self, "_h_build", None):
                try:
                    self._h_build()
                except tk.TclError:
                    pass
        self._dialog_buttons(f, dlg, ok, "✓  Ajouter", GREEN, GREEN_D)
        de.focus_set()

    def _del_hist(self, index, rebuild):
        if not (0 <= index < len(self.historique)):
            return
        h = self.historique[index]
        if not messagebox.askyesno(
                "Supprimer", f"Supprimer le tour {h['tour']} — {h['beneficiaire']} ?\n\n"
                f"{fmt_money(h.get('penalites', 0))} retirés de la caisse, et la personne "
                "repassera à « n'a pas bouffé »."):
            return
        self.caisse = max(0, self.caisse - h.get("penalites", 0))
        if h.get("cycle", 1) == self.cycle:
            m = next((x for x in self.membres if x["nom"] == h["beneficiaire"]), None)
            if m and m.get("recu") and (m.get("date_recu") == h.get("date") or not h.get("date")):
                m["recu"], m["date_recu"] = False, None
            self.tour = max(1, self.tour - 1)
        self.historique.pop(index)
        self._save()
        self._refresh()
        self._status("Séance supprimée.", RED)
        rebuild()

    # ------------------------------ Refresh ------------------------------- #
    def _refresh(self):
        n = len(self.membres)
        cagnotte = self.cotisation * n
        nb_recu = sum(1 for m in self.membres if m["recu"])
        cur, nxt = self._courant(), self._prochain()

        mode_txt = "🎲 tirage au sort" if self.mode == "tirage" else "ordre fixe"
        self.sub_lbl.configure(
            text=f"{self.nom_tontine}  ·  cotisation {fmt_money(self.cotisation)} / membre  ·  {mode_txt}")
        if self.mode == "tirage":
            self.btn_tirage.pack(side="left", padx=(8, 0))
        else:
            self.btn_tirage.pack_forget()
        self.cur_name.configure(text=cur["nom"] if cur else ("— aucun membre —" if not n else "Cycle terminé 🎉"))
        self.cur_sub.configure(text=f"reçoit {fmt_money(cagnotte)}" if cur else "")
        self.next_name.configure(text=nxt["nom"] if nxt else "—")
        self.s_tour.configure(text=f"Cycle {self.cycle} · Tour {self.tour}")
        self.s_pot.configure(text=fmt_money(cagnotte))
        self.s_prog.configure(text=f"{nb_recu} / {n}" if n else "—")
        self.s_caisse.configure(text=fmt_money(self.caisse))

        self.tree.delete(*self.tree.get_children())
        for i, m in enumerate(self.membres):
            s = m["seance"]
            tags = ["even" if i % 2 == 0 else "odd"]
            if m["recu"]:
                statut = "✓ A bouffé" + (f" · {m['date_recu']}" if m.get("date_recu") else "")
                tags.append("done")
            elif m is cur:
                statut = "🍽 Bouffe maintenant"
                tags.append("cur")
            elif m is nxt:
                statut = "⏭ Prochain"
                tags.append("next")
            else:
                statut = "En attente"
            pen = self._penal_membre(m)
            self.tree.insert("", "end", iid=str(i), tags=tuple(tags), values=(
                i + 1, m["nom"], m.get("tel", ""), statut,
                "✓ Payé" if s.get("cotise") else "—", fmt_money(pen) if pen else "—"))

    # ------------------------------ Persistance --------------------------- #
    @staticmethod
    def _int(v, d):
        try:
            return int(v)
        except (ValueError, TypeError):
            return d

    def _load(self):
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as fp:
                d = json.load(fp)
        except (json.JSONDecodeError, OSError):
            self._status("Fichier illisible, on repart à zéro.", RED)
            return
        if not isinstance(d, dict):
            return
        self.nom_tontine = str(d.get("nom", "Ma tontine"))
        self.cotisation = self._int(d.get("cotisation", COTISATION_DEFAUT), COTISATION_DEFAUT)
        self.mode = "tirage" if d.get("mode") == "tirage" else "fixe"
        self.tour = max(1, self._int(d.get("tour", 1), 1))
        self.cycle = max(1, self._int(d.get("cycle", 1), 1))
        self.caisse = self._int(d.get("caisse", 0), 0)
        pen = d.get("penalites", {})
        for k in PENALITES_DEFAUT:
            self.penalites[k] = self._int(pen.get(k, PENALITES_DEFAUT[k]), PENALITES_DEFAUT[k])
        self.historique = d.get("historique", []) if isinstance(d.get("historique"), list) else []
        for m in d.get("membres", []) if isinstance(d.get("membres"), list) else []:
            if not m.get("nom"):
                continue
            sj = m.get("seance", {}) or {}
            sv = seance_vierge()
            if sj.get("presence") in ("present", "absent"):
                sv["presence"] = sj["presence"]
            for k in ("cotise", "retard_physique", "retard_cotisation", "echec_cotisation"):
                sv[k] = bool(sj.get(k, False))
            self.membres.append({"nom": str(m.get("nom", "")), "tel": str(m.get("tel", "")),
                                 "recu": bool(m.get("recu", False)),
                                 "date_recu": m.get("date_recu"), "seance": sv})

    def _save(self):
        data = {"nom": self.nom_tontine, "cotisation": self.cotisation,
                "penalites": self.penalites, "mode": self.mode, "tour": self.tour,
                "cycle": self.cycle, "caisse": self.caisse, "membres": self.membres,
                "historique": self.historique}
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
        except OSError as e:
            messagebox.showerror("Erreur", f"Sauvegarde impossible :\n{e}")

    # ------------------------------ Export PDF ---------------------------- #
    def _export_pdf(self):
        if not self.membres:
            messagebox.showinfo("Rien à exporter", "Ajoutez au moins un membre.")
            return
        path = filedialog.asksaveasfilename(
            title="Exporter en PDF", defaultextension=".pdf",
            initialfile=f"tontine_{datetime.now():%Y-%m-%d}.pdf",
            filetypes=[("Fichier PDF", "*.pdf")])
        if not path:
            return
        try:
            self._write_pdf(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Export échoué :\n{e}")
            return
        self._status(f"PDF exporté : {os.path.basename(path)}", GREEN)
        if messagebox.askyesno("Export réussi", f"PDF créé :\n{path}\n\nL'ouvrir ?"):
            try:
                os.startfile(path)
            except Exception:
                pass

    def _write_pdf(self, path):
        INK = colors.HexColor("#111827")
        SOFT = colors.HexColor("#6b7280")
        LINE = colors.HexColor("#d1d5db")
        HEAD = colors.HexColor("#1f2937")
        ALT = colors.HexColor("#f9fafb")
        MARK = colors.HexColor("#fef3c7")
        doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                                topMargin=1.8 * cm, bottomMargin=1.8 * cm, title=self.nom_tontine)
        S = getSampleStyleSheet()
        st_title = ParagraphStyle("t", parent=S["Normal"], fontSize=22, textColor=INK,
                                  leading=24, fontName="Helvetica-Bold")
        st_right = ParagraphStyle("r", parent=S["Normal"], fontSize=11, textColor=SOFT, alignment=2)
        st_soft = ParagraphStyle("s", parent=S["Normal"], fontSize=9, textColor=SOFT)
        st_h2 = ParagraphStyle("h", parent=S["Normal"], fontSize=12, textColor=INK,
                               fontName="Helvetica-Bold", spaceAfter=4)
        cagnotte = self.cotisation * len(self.membres)
        cur, nxt = self._courant(), self._prochain()
        PW = 17.4 * cm

        def hstyle(extra=None):
            return TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEAD), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 9.5),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TEXTCOLOR", (0, 1), (-1, -1), INK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALT]),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE)] + (extra or []))

        ent = Table([[Paragraph(self.nom_tontine, st_title),
                      Paragraph(f"Relevé de tontine<br/>{datetime.now():%d/%m/%Y à %H:%M}<br/>"
                                f"Cycle {self.cycle} · Tour {self.tour}", st_right)]],
                    colWidths=[PW * 0.58, PW * 0.42])
        ent.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                 ("LINEBELOW", (0, 0), (-1, -1), 1.0, INK),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        story = [ent, Spacer(1, 0.35 * cm)]

        nb_recu = sum(1 for m in self.membres if m["recu"])
        meta = Table([
            ["Cotisation / membre", fmt_money(self.cotisation), "Cagnotte du tour", fmt_money(cagnotte)],
            ["Membres", str(len(self.membres)), "Caisse (épargne)", fmt_money(self.caisse)],
            ["Ont déjà bouffé", f"{nb_recu} / {len(self.membres)}", "Bouffe maintenant",
             cur["nom"] if cur else "—"],
            ["", "", "Prochain à bouffer", nxt["nom"] if nxt else "—"],
        ], colWidths=[PW * 0.25, PW * 0.25, PW * 0.27, PW * 0.23])
        meta.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica"), ("FONTNAME", (2, 0), (2, -1), "Helvetica"),
            ("TEXTCOLOR", (0, 0), (0, -1), SOFT), ("TEXTCOLOR", (2, 0), (2, -1), SOFT),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"), ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (1, 0), (1, -1), INK), ("TEXTCOLOR", (3, 0), (3, -1), INK),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("FONTSIZE", (3, 2), (3, 2), 11), ("BACKGROUND", (3, 2), (3, 2), MARK)]))
        story += [meta, Spacer(1, 0.5 * cm), Paragraph("Membres", st_h2)]

        data = [["#", "Membre", "Téléphone", "Statut"]]
        for i, m in enumerate(self.membres, 1):
            if m["recu"]:
                stt = "A bouffé" + (f" le {m['date_recu']}" if m.get("date_recu") else "")
            elif m is cur:
                stt = "Bouffe maintenant"
            elif m is nxt:
                stt = "Prochain à bouffer"
            else:
                stt = "En attente"
            data.append([str(i), m["nom"], m.get("tel", ""), stt])
        tbl = Table(data, colWidths=[1.0 * cm, 6.4 * cm, 4.0 * cm, 6.0 * cm], repeatRows=1)
        extra = [("ALIGN", (0, 0), (0, -1), "CENTER")]
        for marker, col in ((cur, "#dcfce7"), (nxt, "#dbeafe")):
            if marker is not None:
                r = self.membres.index(marker) + 1
                extra += [("BACKGROUND", (0, r), (-1, r), colors.HexColor(col)),
                          ("FONTNAME", (1, r), (1, r), "Helvetica-Bold"),
                          ("FONTNAME", (3, r), (3, r), "Helvetica-Bold")]
        tbl.setStyle(hstyle(extra))
        story.append(tbl)

        if self.historique:
            story += [Spacer(1, 0.5 * cm), Paragraph("Historique des séances", st_h2)]
            hd = [["Cycle", "Tour", "Date", "Bénéficiaire", "Cagnotte", "Pénalités"]]
            for h in self.historique:
                hd.append([str(h.get("cycle", 1)), str(h["tour"]), h.get("date", ""),
                           h["beneficiaire"], fmt_money(h["cagnotte"]), fmt_money(h["penalites"])])
            ht = Table(hd, colWidths=[1.4 * cm, 1.3 * cm, 2.6 * cm, 5.1 * cm, 3.5 * cm, 3.5 * cm],
                       repeatRows=1)
            ht.setStyle(hstyle([("ALIGN", (0, 0), (1, -1), "CENTER"),
                                ("ALIGN", (4, 0), (-1, -1), "RIGHT")]))
            story.append(ht)

        lp = []
        for h in self.historique:
            for d in h.get("details", []):
                lp.append([h.get("date", ""), d["nom"], ", ".join(d.get("motifs", [])),
                           fmt_money(d["montant"])])
        if lp:
            story += [Spacer(1, 0.5 * cm), Paragraph("Détail des pénalités", st_h2)]
            pd = [["Date", "Membre", "Motif(s)", "Montant"]] + lp
            pd.append(["", "", "Total caisse", fmt_money(self.caisse)])
            pt = Table(pd, colWidths=[2.6 * cm, 4.6 * cm, 6.7 * cm, 3.5 * cm], repeatRows=1)
            pt.setStyle(hstyle([("ALIGN", (3, 0), (3, -1), "RIGHT"),
                                ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
                                ("BACKGROUND", (0, -1), (-1, -1), ALT),
                                ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK)]))
            story.append(pt)

        story += [Spacer(1, 0.6 * cm),
                  Paragraph(f"{APP_NAME} — document généré automatiquement.", st_soft)]
        doc.build(story)


if __name__ == "__main__":
    TontinoApp().mainloop()
