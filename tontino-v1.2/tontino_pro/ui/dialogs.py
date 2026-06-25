"""Toutes les fenêtres modales : réglages, pointage, séances (par type), historique."""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ..config import (TYPES, ORDRES, PENALITES_DEFAUT, PENALITES_LABELS,
                      GREEN, GREEN_D, RED, RED_D, AMBER, SLATE, SLATE_D, BLUE, BLUE_D)
from ..utils import fmt_money, parse_int, today
from ..engines import get_engine
from .widgets import make_dialog, dialog_buttons, button


# --------------------------------------------------------------------------- #
#  Membre : édition
# --------------------------------------------------------------------------- #
def edit_membre(app):
    i = app.selected_index()
    if i is None:
        app.set_status("Sélectionnez un membre.", RED)
        return
    m = app.tontine.membres[i]
    dlg, f = make_dialog(app, "Modifier le membre", 430, 270)
    ctk.CTkLabel(f, text="✏  Modifier", font=ctk.CTkFont(size=16, weight="bold")).pack(
        anchor="w", pady=(0, 14))
    nv, tv = tk.StringVar(value=m.nom), tk.StringVar(value=m.tel)
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
        m.nom, m.tel = nom, tv.get().strip()
        app.save()
        app.refresh()
        app.set_status(f"« {nom} » modifié.", GREEN)
        dlg.destroy()
    dialog_buttons(f, dlg, ok)
    e.focus_set()
    dlg.bind("<Return>", lambda ev: ok())


# --------------------------------------------------------------------------- #
#  Réglages
# --------------------------------------------------------------------------- #
def settings(app):
    t = app.tontine
    dlg, f = make_dialog(app, "Réglages de la tontine", 480, 620)
    ctk.CTkLabel(f, text="⚙  Réglages", font=ctk.CTkFont(size=16, weight="bold")).pack(
        anchor="w", pady=(0, 12))

    nv = tk.StringVar(value=t.nom)
    ctk.CTkLabel(f, text="Nom de la tontine", text_color=("gray40", "gray70")).pack(anchor="w")
    ctk.CTkEntry(f, textvariable=nv, height=34).pack(fill="x", pady=(2, 10))

    ctk.CTkLabel(f, text="Type de tontine", text_color=("gray40", "gray70")).pack(anchor="w")
    id_by_label = {v: k for k, v in TYPES.items()}
    type_var = tk.StringVar(value=TYPES[t.type])
    ctk.CTkOptionMenu(f, variable=type_var, values=list(TYPES.values())).pack(fill="x", pady=(2, 10))

    ctk.CTkLabel(f, text="Ordre de passage (rotative)", text_color=("gray40", "gray70")).pack(anchor="w")
    ordre_seg = ctk.CTkSegmentedButton(f, values=[ORDRES["fixe"], ORDRES["tirage"]])
    ordre_seg.set(ORDRES[t.ordre])
    ordre_seg.pack(fill="x", pady=(2, 10))

    cv = tk.StringVar(value=str(t.cotisation))
    ctk.CTkLabel(f, text="Cotisation par membre / séance (FCFA)",
                 text_color=("gray40", "gray70")).pack(anchor="w")
    ctk.CTkEntry(f, textvariable=cv, height=34).pack(fill="x", pady=(2, 10))

    ctk.CTkLabel(f, text="Pénalités (→ caisse)", font=ctk.CTkFont(weight="bold")).pack(
        anchor="w", pady=(2, 4))
    pv = {}
    for k in ("absence", "retard_physique", "retard_cotisation", "echec_cotisation"):
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=PENALITES_LABELS[k]).pack(side="left")
        v = tk.StringVar(value=str(t.penalites[k]))
        pv[k] = v
        ctk.CTkEntry(row, textvariable=v, width=120, height=30).pack(side="right")

    def ok():
        t.nom = nv.get().strip() or "Ma tontine"
        new_type = id_by_label.get(type_var.get(), "rotative")
        t.type = new_type
        t.ordre = "tirage" if ordre_seg.get() == ORDRES["tirage"] else "fixe"
        t.cotisation = parse_int(cv.get())
        for k, v in pv.items():
            t.penalites[k] = parse_int(v.get())
        app.engine = get_engine(t.type)
        app.save()
        app.refresh()
        app.set_status("Réglages enregistrés.", GREEN)
        dlg.destroy()
    dialog_buttons(f, dlg, ok)


# --------------------------------------------------------------------------- #
#  Pointage (présence + pénalités)
# --------------------------------------------------------------------------- #
def pointage(app):
    if not app.engine.uses_penalties:
        app.set_status("Pas de pointage de pénalités pour ce type de tontine.", AMBER)
        return
    i = app.selected_index()
    if i is None:
        app.set_status("Sélectionnez un membre à pointer.", RED)
        return
    t = app.tontine
    m = t.membres[i]
    s = m.seance
    dlg, f = make_dialog(app, f"Pointage — {m.nom}", 460, 460)
    ctk.CTkLabel(f, text=f"📝  Pointage · Tour {t.tour}",
                 font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(f, text=m.nom, text_color=("gray40", "gray70")).pack(anchor="w", pady=(0, 12))
    pres = tk.StringVar(value=s.get("presence") or "present")
    cot = tk.BooleanVar(value=s.get("cotise", False))
    rp = tk.BooleanVar(value=s.get("retard_physique", False))
    rc = tk.BooleanVar(value=s.get("retard_cotisation", False))
    ec = tk.BooleanVar(value=s.get("echec_cotisation", False))
    tot = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color=AMBER)

    def recompute(*_):
        p, x = t.penalites, 0
        if pres.get() == "absent":
            x += p["absence"]
        if rp.get():
            x += p["retard_physique"]
        if rc.get():
            x += p["retard_cotisation"]
        if ec.get():
            x += p["echec_cotisation"]
        tot.configure(text=f"Pénalités → caisse : {fmt_money(x)}")

    pr = ctk.CTkFrame(f, fg_color="transparent")
    pr.pack(anchor="w", pady=(0, 6))
    ctk.CTkLabel(pr, text="Présence :").pack(side="left", padx=(0, 10))
    ctk.CTkRadioButton(pr, text="Présent", variable=pres, value="present",
                       command=recompute).pack(side="left", padx=(0, 10))
    ctk.CTkRadioButton(pr, text=f"Absent (+{t.penalites['absence']})", variable=pres,
                       value="absent", command=recompute).pack(side="left")
    ctk.CTkCheckBox(f, text=f"A payé sa cotisation ({fmt_money(t.cotisation)})",
                    variable=cot, command=recompute).pack(anchor="w", pady=(8, 4))
    ctk.CTkLabel(f, text="Pénalités :", text_color=("gray40", "gray70")).pack(anchor="w", pady=(8, 2))
    ctk.CTkCheckBox(f, text=f"Retard physique (+{t.penalites['retard_physique']})",
                    variable=rp, command=recompute).pack(anchor="w", pady=4)
    ctk.CTkCheckBox(f, text=f"Retard cotisation (+{t.penalites['retard_cotisation']})",
                    variable=rc, command=recompute).pack(anchor="w", pady=4)
    ctk.CTkCheckBox(f, text=f"Échec cotisation (+{t.penalites['echec_cotisation']})",
                    variable=ec, command=recompute).pack(anchor="w", pady=4)
    tot.pack(anchor="w", pady=(14, 12))
    recompute()

    def ok():
        s.update(presence=pres.get(), cotise=cot.get(), retard_physique=rp.get(),
                 retard_cotisation=rc.get(), echec_cotisation=ec.get())
        app.save()
        app.refresh()
        if str(i) in app.tree.get_children():
            app.tree.selection_set(str(i))
        app.set_status(f"Pointage de « {m.nom} » enregistré.", GREEN)
        dlg.destroy()
    dialog_buttons(f, dlg, ok)


# --------------------------------------------------------------------------- #
#  Séances : une fonction par type
# --------------------------------------------------------------------------- #
def _date_field(parent, label="Date de la séance (jj/mm/aaaa)", default=None):
    ctk.CTkLabel(parent, text=label, text_color=("gray40", "gray70")).pack(anchor="w")
    var = tk.StringVar(value=default if default is not None else today())
    ctk.CTkEntry(parent, textvariable=var, width=180, height=34).pack(anchor="w", pady=(2, 12))
    return var


def session_rotative(app):
    t, e = app.tontine, app.engine
    restants = t.restants()
    if not restants:
        messagebox.showinfo("Terminé", "Tout le monde a bénéficié. Lancez un nouveau cycle."
                            if t.membres else "Ajoutez d'abord des membres.")
        return
    dlg, f = make_dialog(app, "Valider la séance", 480, 400)
    ctk.CTkLabel(f, text=f"✓  Valider la séance · Tour {t.tour}",
                 font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 12))
    ctk.CTkLabel(f, text="🍽  Qui bouffe (reçoit la cagnotte) ?",
                 text_color=("gray40", "gray70")).pack(anchor="w")
    bvar = tk.StringVar(value=(e.current(t) or restants[0]).nom)
    ctk.CTkOptionMenu(f, variable=bvar, values=[m.nom for m in restants]).pack(fill="x", pady=(2, 12))
    ctk.CTkLabel(f, text=f"💰 Cagnotte : {fmt_money(t.cagnotte())}   ·   "
                         f"🏦 Pénalités : {fmt_money(t.penalites_seance())}",
                 justify="left").pack(anchor="w", pady=(0, 6))
    dvar = _date_field(f)

    def ok():
        if e.validate(t, bvar.get(), dvar.get().strip() or today()):
            app.save()
            app.refresh()
            app.set_status(f"{bvar.get()} a bouffé.", GREEN)
            _rebuild_history(app)
            dlg.destroy()
    dialog_buttons(f, dlg, ok, "✓  Valider", GREEN, GREEN_D)


def session_enchere(app):
    t, e = app.tontine, app.engine
    restants = t.restants()
    if not restants:
        messagebox.showinfo("Terminé", "Tout le monde a gagné. Lancez un nouveau cycle."
                            if t.membres else "Ajoutez d'abord des membres.")
        return
    dlg, f = make_dialog(app, "Adjuger l'enchère", 480, 430)
    ctk.CTkLabel(f, text=f"🔨  Adjuger l'enchère · Tour {t.tour}",
                 font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 12))
    ctk.CTkLabel(f, text="🏆  Qui remporte la cagnotte (plus offrant) ?",
                 text_color=("gray40", "gray70")).pack(anchor="w")
    bvar = tk.StringVar(value=restants[0].nom)
    ctk.CTkOptionMenu(f, variable=bvar, values=[m.nom for m in restants]).pack(fill="x", pady=(2, 10))
    ctk.CTkLabel(f, text="Montant de la mise gagnante (→ caisse, FCFA)",
                 text_color=("gray40", "gray70")).pack(anchor="w")
    mvar = tk.StringVar(value="0")
    ctk.CTkEntry(f, textvariable=mvar, height=34).pack(fill="x", pady=(2, 10))
    ctk.CTkLabel(f, text=f"💰 Cagnotte remportée : {fmt_money(t.cagnotte())}",
                 ).pack(anchor="w", pady=(0, 6))
    dvar = _date_field(f)

    def ok():
        if e.validate(t, bvar.get(), dvar.get().strip() or today(), parse_int(mvar.get())):
            app.save()
            app.refresh()
            app.set_status(f"{bvar.get()} remporte l'enchère.", GREEN)
            _rebuild_history(app)
            dlg.destroy()
    dialog_buttons(f, dlg, ok, "🔨  Adjuger", GREEN, GREEN_D)


def session_epargne(app):
    t, e = app.tontine, app.engine
    if not t.membres:
        messagebox.showinfo("Aucun membre", "Ajoutez d'abord des membres.")
        return
    dlg, f = make_dialog(app, "Encaisser une séance d'épargne", 480, 560)
    ctk.CTkLabel(f, text=f"💰  Collecte d'épargne · Séance {t.tour}",
                 font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 8))
    ctk.CTkLabel(f, text="Montant déposé par chaque membre (FCFA) :",
                 text_color=("gray40", "gray70")).pack(anchor="w", pady=(0, 4))
    box = ctk.CTkScrollableFrame(f, label_text="", height=280)
    box.pack(fill="x", pady=(0, 8))
    vars_ = {}
    for m in t.membres:
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=m.nom, anchor="w", width=200).pack(side="left")
        v = tk.StringVar(value=str(t.cotisation))
        vars_[m.nom] = v
        ctk.CTkEntry(row, textvariable=v, width=130, height=30).pack(side="right")
    dvar = _date_field(f)

    def ok():
        depots = {nom: parse_int(v.get()) for nom, v in vars_.items()}
        sess = e.collect(t, depots, dvar.get().strip() or today())
        app.save()
        app.refresh()
        app.set_status(f"Collecte : {fmt_money(sess.montant)} encaissés.", GREEN)
        _rebuild_history(app)
        dlg.destroy()
    dialog_buttons(f, dlg, ok, "💰  Encaisser", GREEN, GREEN_D)


def distribute_epargne(app):
    t, e = app.tontine, app.engine
    if t.fonds <= 0:
        messagebox.showinfo("Fonds vide", "Il n'y a rien à distribuer pour le moment.")
        return
    dlg, f = make_dialog(app, "Distribuer le fonds", 470, 340)
    ctk.CTkLabel(f, text="📤  Distribuer le fonds",
                 font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 8))
    ctk.CTkLabel(f, text=f"Fonds à distribuer : {fmt_money(t.fonds)}  ·  {len(t.membres)} membre(s)",
                 ).pack(anchor="w", pady=(0, 10))
    ctk.CTkLabel(f, text="Mode de répartition", text_color=("gray40", "gray70")).pack(anchor="w")
    seg = ctk.CTkSegmentedButton(f, values=["À parts égales", "Au prorata de l'épargne"])
    seg.set("À parts égales")
    seg.pack(fill="x", pady=(2, 10))
    dvar = _date_field(f, "Date de la distribution")
    ctk.CTkLabel(f, text="⚠ Cela clôture le cycle d'épargne (fonds et épargnes remis à zéro).",
                 text_color=AMBER, font=ctk.CTkFont(size=11)).pack(anchor="w")

    def ok():
        mode = "prorata" if seg.get() == "Au prorata de l'épargne" else "egal"
        sess = e.distribute(t, dvar.get().strip() or today(), mode)
        app.save()
        app.refresh()
        if sess:
            app.set_status(f"Fonds distribué ({fmt_money(sess.montant)}).", GREEN)
        _rebuild_history(app)
        dlg.destroy()
    dialog_buttons(f, dlg, ok, "📤  Distribuer", GREEN, GREEN_D)


# --------------------------------------------------------------------------- #
#  Historique
# --------------------------------------------------------------------------- #
def _rebuild_history(app):
    fn = getattr(app, "_hist_build", None)
    if fn:
        try:
            fn()
        except tk.TclError:
            pass


def history(app):
    t = app.tontine
    dlg, f = make_dialog(app, "Historique des séances", 780, 560)
    ctk.CTkLabel(f, text="📜  Historique des séances",
                 font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
    info = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13, weight="bold"), text_color=AMBER)
    info.pack(anchor="w", pady=(2, 8))

    if t.type in ("rotative", "encheres"):
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        add_cmd = session_enchere if t.type == "encheres" else session_rotative
        button(bar, "➕  Ajouter une séance", lambda: add_cmd(app), GREEN, GREEN_D,
               width=200).pack(side="left")
        ctk.CTkLabel(bar, text="  (choisissez le bénéficiaire et la date — pour saisir votre cahier)",
                     text_color=("gray40", "gray70")).pack(side="left")

    content = ctk.CTkScrollableFrame(f, label_text="")
    content.pack(fill="both", expand=True, pady=(0, 12))

    def build():
        for w in content.winfo_children():
            w.destroy()
        if t.type == "epargne":
            info.configure(text=f"Fonds : {fmt_money(t.fonds)}   ·   Cycle {t.cycle} · Séance {t.tour}")
        else:
            info.configure(text=f"Caisse : {fmt_money(t.caisse)}   ·   Cycle {t.cycle} · Tour {t.tour}")
        if not t.historique:
            ctk.CTkLabel(content, text="Aucune séance enregistrée.",
                         text_color=("gray40", "gray70")).pack(anchor="w", pady=18)
            return
        for idx, s in enumerate(t.historique):
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill="x")
            if s.type.startswith("epargne"):
                op = "Distribution" if s.type == "epargne_distrib" else "Collecte"
                txt = f"Cycle {s.cycle} · Séance {s.tour} · {s.date} · {op} : {fmt_money(s.montant)}"
            elif s.type == "encheres":
                txt = (f"Cycle {s.cycle} · Tour {s.tour} · {s.date} · 🏆 {s.beneficiaire} · "
                       f"{fmt_money(s.montant)} · mise {fmt_money(s.mise)}")
            else:
                txt = (f"Cycle {s.cycle} · Tour {s.tour} · {s.date} · {s.beneficiaire} · "
                       f"{fmt_money(s.montant)} · pénal. {fmt_money(s.penalites)}")
            ctk.CTkLabel(row, text=txt, anchor="w").pack(side="left", padx=4, pady=2)
            button(row, "🗑", lambda i=idx: _delete_session(app, i, build), RED, RED_D,
                   width=34).pack(side="right", padx=4)
            for d in s.details:
                if "motifs" in d:
                    line = f"        ⤷ {d['nom']} : {', '.join(d.get('motifs', []))} — {fmt_money(d['montant'])}"
                else:
                    line = f"        ⤷ {d['nom']} : {fmt_money(d.get('montant', 0))}"
                ctk.CTkLabel(content, text=line, anchor="w", font=ctk.CTkFont(size=11),
                             text_color=("gray45", "gray60")).pack(fill="x", padx=10)

    app._hist_build = build
    build()
    button(f, "Fermer", dlg.destroy, BLUE, BLUE_D, width=110).pack(anchor="e")


def _delete_session(app, index, rebuild):
    t = app.tontine
    if not (0 <= index < len(t.historique)):
        return
    s = t.historique[index]
    if s.type == "epargne_distrib":
        messagebox.showinfo("Impossible",
                            "Une distribution ne peut pas être annulée automatiquement.")
        return
    if not messagebox.askyesno("Supprimer", f"Supprimer cette séance du {s.date} ?"):
        return
    if s.type == "epargne_depot":
        t.fonds = max(0, t.fonds - s.montant)
        for d in s.details:
            m = next((x for x in t.membres if x.nom == d.get("nom")), None)
            if m:
                m.epargne = max(0, m.epargne - d.get("montant", 0))
        if s.cycle == t.cycle:
            t.tour = max(1, t.tour - 1)
    else:  # rotative / encheres
        t.caisse = max(0, t.caisse - s.penalites - s.mise)
        if s.cycle == t.cycle:
            m = next((x for x in t.membres if x.nom == s.beneficiaire), None)
            if m and m.recu and (m.date_recu == s.date or not s.date):
                m.recu, m.date_recu = False, None
            t.tour = max(1, t.tour - 1)
    t.historique.pop(index)
    app.save()
    app.refresh()
    app.set_status("Séance supprimée.", RED)
    rebuild()
