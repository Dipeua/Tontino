"""Fenêtre principale de Tontino-Pro.

L'application est volontairement « bête » : elle affiche ce que le MOTEUR du
type de tontine courant lui dit d'afficher (cartes, stats, lignes du tableau)
et lui délègue les actions. Changer de type = changer de moteur.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import customtkinter as ctk

from .. import storage
from ..config import (APP_NAME, APP_SUBTITLE, TYPES, ORDRES,
                      BLUE, BLUE_D, GREEN, GREEN_D, RED, RED_D, AMBER, AMBER_D,
                      SLATE, SLATE_D, CYAN, CYAN_D, PRIMARY_BG, SECONDARY_BG)
from ..engines import get_engine
from ..models import Member
from ..utils import fmt_money
from . import theme, dialogs
from .widgets import button


class TontinoProApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        theme.setup()
        self.title(f"{APP_NAME} — {APP_SUBTITLE}")
        self.geometry("1080x820")
        self.minsize(960, 740)

        self.tontine = storage.load()
        self.engine = get_engine(self.tontine.type)

        self._build()
        self.refresh()
        self.bind("<Control-s>", lambda e: self.export_pdf())

    # ------------------------------ Services ------------------------------ #
    def save(self):
        try:
            storage.save(self.tontine)
        except OSError as e:
            messagebox.showerror("Erreur", f"Sauvegarde impossible :\n{e}")

    def set_status(self, msg, color=None):
        self.status.configure(text=msg, text_color=color or ("gray40", "gray70"))

    def selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except (ValueError, IndexError):
            return None

    # ------------------------------ Construction -------------------------- #
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self._build_topbar()
        self._build_spotlight()
        self._build_stats()
        self._build_form()
        self._build_body()
        self.status = ctk.CTkLabel(self, text="Prêt.", anchor="w",
                                   text_color=("gray40", "gray70"), font=ctk.CTkFont(size=12))
        self.status.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 10))

    def _build_topbar(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 4))
        top.grid_columnconfigure(0, weight=1)
        box = ctk.CTkFrame(top, fg_color="transparent")
        box.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(box, text="🤝  " + APP_NAME,
                     font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        self.sub_lbl = ctk.CTkLabel(box, text="", text_color=("gray40", "gray70"),
                                    font=ctk.CTkFont(size=12))
        self.sub_lbl.pack(anchor="w")
        rb = ctk.CTkFrame(top, fg_color="transparent")
        rb.grid(row=0, column=1, sticky="e")
        self.mode_sw = ctk.CTkSegmentedButton(rb, values=["☀", "🌙"],
                                              command=self._toggle_mode, width=80)
        self.mode_sw.set("☀")
        self.mode_sw.pack(side="left", padx=(0, 10))
        button(rb, "⚙  Réglages", lambda: dialogs.settings(self),
               SLATE, SLATE_D, width=120).pack(side="left")

    def _spot_card(self, parent, col, bg):
        card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=16)
        card.grid(row=0, column=col, sticky="ew", padx=(0, 8) if col == 0 else (8, 0))
        lab = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=12, weight="bold"))
        lab.pack(anchor="w", padx=18, pady=(14, 0))
        val = ctk.CTkLabel(card, text="—", font=ctk.CTkFont(size=23, weight="bold"))
        val.pack(anchor="w", padx=18)
        sub = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=12))
        sub.pack(anchor="w", padx=18, pady=(0, 10))
        return card, lab, val, sub

    def _build_spotlight(self):
        spot = ctk.CTkFrame(self, fg_color="transparent")
        spot.grid(row=1, column=0, sticky="ew", padx=22, pady=8)
        spot.grid_columnconfigure((0, 1), weight=1)
        self.cur_card, self.cur_lbl, self.cur_val, self.cur_sub = self._spot_card(spot, 0, PRIMARY_BG)
        # rangée de boutons sur la carte principale
        row = ctk.CTkFrame(self.cur_card, fg_color="transparent")
        row.pack(anchor="w", padx=18, pady=(0, 16), fill="x")
        self.btn_primary = button(row, "✓  Valider", lambda: None, GREEN, GREEN_D,
                                  width=190, height=36)
        self.btn_draw = button(row, "🎲  Tirer au sort", self._draw, AMBER, AMBER_D,
                               width=150, height=36)
        self.btn_extra = button(row, "📤  Action", lambda: None, BLUE, BLUE_D,
                                width=170, height=36)
        self._btn_row = row
        self.nxt_card, self.nxt_lbl, self.nxt_val, self.nxt_sub = self._spot_card(spot, 1, SECONDARY_BG)

    def _build_stats(self):
        stats = ctk.CTkFrame(self, corner_radius=12)
        stats.grid(row=2, column=0, sticky="ew", padx=22, pady=(2, 8))
        self.chips = []
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1)
            c = ctk.CTkFrame(stats, fg_color="transparent")
            c.grid(row=0, column=i, sticky="ew", padx=14, pady=12)
            lab = ctk.CTkLabel(c, text="", font=ctk.CTkFont(size=10, weight="bold"),
                               text_color=("gray45", "gray60"))
            lab.pack(anchor="w")
            val = ctk.CTkLabel(c, text="—", font=ctk.CTkFont(size=15, weight="bold"))
            val.pack(anchor="w")
            self.chips.append((lab, val))

    def _build_form(self):
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
        button(form, "＋  Ajouter", self._add_membre, width=130).grid(
            row=0, column=2, padx=(0, 14), pady=14)
        self.nom_entry.bind("<Return>", lambda e: self._add_membre())
        self.tel_entry.bind("<Return>", lambda e: self._add_membre())

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=4, column=0, sticky="nsew", padx=22, pady=(0, 6))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        acts = ctk.CTkFrame(body, fg_color="transparent")
        acts.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.btn_pointage = button(acts, "📝  Pointer", lambda: dialogs.pointage(self),
                                   GREEN, GREEN_D, width=110)
        self.btn_pointage.pack(side="left")
        button(acts, "✏  Modifier", lambda: dialogs.edit_membre(self), CYAN, CYAN_D,
               width=100).pack(side="left", padx=(8, 0))
        button(acts, "↑", self._up, SLATE, SLATE_D, width=40).pack(side="left", padx=(8, 0))
        button(acts, "↓", self._down, SLATE, SLATE_D, width=40).pack(side="left", padx=(6, 0))
        button(acts, "🗑  Retirer", self._del_membre, RED, RED_D, width=100).pack(side="left", padx=(8, 0))
        button(acts, "📜  Historique", lambda: dialogs.history(self), SLATE, SLATE_D,
               width=120).pack(side="right")
        button(acts, "⬇  PDF", self.export_pdf, "#0ea5e9", "#0284c7", width=80).pack(
            side="right", padx=(0, 8))
        button(acts, "🔄  Nouveau cycle", self._new_cycle, AMBER, AMBER_D, width=150).pack(
            side="right", padx=(0, 8))

        wrap = ctk.CTkFrame(body, corner_radius=12)
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        self.style = ttk.Style()
        cols = ("ordre", "nom", "tel", "statut", "info1", "info2")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("ordre", text="#")
        self.tree.heading("nom", text="Membre")
        self.tree.heading("tel", text="Téléphone")
        self.tree.column("ordre", width=44, anchor="center", stretch=False)
        self.tree.column("nom", width=210, anchor="w")
        self.tree.column("tel", width=130, anchor="w")
        self.tree.column("statut", width=210, anchor="w")
        self.tree.column("info1", width=110, anchor="center", stretch=False)
        self.tree.column("info2", width=100, anchor="e", stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=8, padx=(0, 8))
        self.tree.bind("<Double-1>", lambda e: dialogs.pointage(self))
        self.tree.bind("<Delete>", lambda e: self._del_membre())
        theme.style_tree(self.style, self.tree)

    # ------------------------------ Actions membres ----------------------- #
    def _add_membre(self):
        nom = self.nom_var.get().strip()
        if not nom:
            messagebox.showwarning("Champ manquant", "Entrez le nom du membre.")
            return
        if any(m.nom.lower() == nom.lower() for m in self.tontine.membres):
            if not messagebox.askyesno("Doublon", f"« {nom} » existe déjà. L'ajouter quand même ?"):
                return
        self.tontine.membres.append(Member(nom=nom, tel=self.tel_var.get().strip()))
        self.nom_var.set("")
        self.tel_var.set("")
        self.nom_entry.focus_set()
        self.save()
        self.refresh()
        self.set_status(f"« {nom} » ajouté.", GREEN)

    def _del_membre(self):
        i = self.selected_index()
        if i is None:
            self.set_status("Sélectionnez un membre.", RED)
            return
        m = self.tontine.membres[i]
        if messagebox.askyesno("Retirer", f"Retirer « {m.nom} » ?"):
            self.tontine.membres.pop(i)
            self.save()
            self.refresh()
            self.set_status(f"« {m.nom} » retiré.", RED)

    def _up(self):
        i = self.selected_index()
        if i and i > 0:
            ms = self.tontine.membres
            ms[i - 1], ms[i] = ms[i], ms[i - 1]
            self.save()
            self.refresh()
            self.tree.selection_set(str(i - 1))

    def _down(self):
        i = self.selected_index()
        if i is not None and i < len(self.tontine.membres) - 1:
            ms = self.tontine.membres
            ms[i + 1], ms[i] = ms[i], ms[i + 1]
            self.save()
            self.refresh()
            self.tree.selection_set(str(i + 1))

    def _draw(self):
        if not self.engine.can_draw(self.tontine):
            return
        if not messagebox.askyesno("Tirage au sort",
                                   "Tirer au sort l'ordre des membres qui n'ont pas encore bénéficié ?"):
            return
        if self.engine.draw(self.tontine):
            self.save()
            self.refresh()
            cur = self.engine.current(self.tontine)
            self.set_status(f"🎲 Tirage effectué — {cur.nom} en premier." if cur else "Tirage effectué.", GREEN)
        else:
            self.set_status("Pas assez de membres à tirer.", AMBER)

    def _new_cycle(self):
        if not self.tontine.membres:
            return
        if not messagebox.askyesno("Nouveau cycle",
                                   "Démarrer un nouveau cycle ?\n\nTout repart à zéro pour ce cycle "
                                   "(la caisse et l'historique sont conservés)."):
            return
        self.engine.new_cycle(self.tontine)
        self.save()
        self.refresh()
        self.set_status(f"Cycle {self.tontine.cycle} démarré.", GREEN)

    def _dispatch(self, key):
        {"validate": dialogs.session_rotative,
         "enchere": dialogs.session_enchere,
         "epargne": dialogs.session_epargne,
         "distribute": dialogs.distribute_epargne}.get(key, lambda app: None)(self)

    def export_pdf(self):
        if not self.tontine.membres:
            messagebox.showinfo("Rien à exporter", "Ajoutez au moins un membre.")
            return
        from datetime import datetime
        path = filedialog.asksaveasfilename(
            title="Exporter en PDF", defaultextension=".pdf",
            initialfile=f"tontine_{datetime.now():%Y-%m-%d}.pdf",
            filetypes=[("Fichier PDF", "*.pdf")])
        if not path:
            return
        try:
            from .. import pdf_export
            pdf_export.export(self.tontine, self.engine, path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Export échoué :\n{e}")
            return
        self.set_status(f"PDF exporté : {path}", GREEN)
        if messagebox.askyesno("Export réussi", f"PDF créé :\n{path}\n\nL'ouvrir ?"):
            import os
            try:
                os.startfile(path)
            except Exception:
                pass

    def _toggle_mode(self, v):
        ctk.set_appearance_mode("dark" if v == "🌙" else "light")
        theme.style_tree(self.style, self.tree)
        self.refresh()

    # ------------------------------ Rafraîchissement ---------------------- #
    def refresh(self):
        t, e = self.tontine, self.engine
        ordre_txt = f" · {ORDRES.get(t.ordre, '')}" if t.type == "rotative" else ""
        self.sub_lbl.configure(text=f"{t.nom}  ·  {TYPES.get(t.type, t.type)}{ordre_txt}")

        cards = e.cards(t)
        p, s = cards["primary"], cards["secondary"]
        self.cur_lbl.configure(text=p["label"])
        self.cur_val.configure(text=p["value"])
        self.cur_sub.configure(text=p["sub"])
        self.nxt_lbl.configure(text=s["label"])
        self.nxt_val.configure(text=s["value"])
        self.nxt_sub.configure(text=s["sub"])

        # boutons de la carte principale
        for b in (self.btn_primary, self.btn_draw, self.btn_extra):
            b.pack_forget()
        act = cards["action"]
        self.btn_primary.configure(text=act["label"], command=lambda k=act["key"]: self._dispatch(k))
        self.btn_primary.pack(side="left")
        if cards.get("can_draw"):
            self.btn_draw.pack(side="left", padx=(8, 0))
        if cards.get("extra"):
            ex = cards["extra"][0]
            self.btn_extra.configure(text=ex["label"], command=lambda k=ex["key"]: self._dispatch(k))
            self.btn_extra.pack(side="left", padx=(8, 0))

        # stats
        st = e.stats(t)
        for i, (lab, val) in enumerate(self.chips):
            if i < len(st):
                lab.configure(text=st[i][0])
                val.configure(text=st[i][1])
            else:
                lab.configure(text="")
                val.configure(text="")

        # bouton pointer pertinent ?
        self.btn_pointage.configure(state="normal" if e.uses_penalties else "disabled")

        # en-têtes du tableau
        h = e.table_headers()
        self.tree.heading("statut", text=h[0])
        self.tree.heading("info1", text=h[1])
        self.tree.heading("info2", text=h[2])

        # lignes
        self.tree.delete(*self.tree.get_children())
        for i, m in enumerate(t.membres):
            r = e.member_row(t, m)
            tags = ["even" if i % 2 == 0 else "odd"]
            if r["tag"]:
                tags.append(r["tag"])
            self.tree.insert("", "end", iid=str(i), tags=tuple(tags),
                             values=(i + 1, m.nom, m.tel, r["statut"], r["info1"], r["info2"]))


def main():
    TontinoProApp().mainloop()
