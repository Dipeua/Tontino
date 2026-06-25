"""Widgets et helpers réutilisables (boutons, fenêtres modales)."""

import customtkinter as ctk

from ..config import BLUE, BLUE_D, SLATE, SLATE_D


def button(parent, text, command, color=BLUE, hover=BLUE_D, width=140, height=None):
    kw = dict(text=text, command=command, fg_color=color, hover_color=hover, width=width)
    if height:
        kw["height"] = height
    return ctk.CTkButton(parent, **kw)


def make_dialog(app, title, w, h):
    """Crée une fenêtre modale centrée sur la fenêtre principale."""
    dlg = ctk.CTkToplevel(app)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.transient(app)
    app.update_idletasks()
    x = app.winfo_rootx() + (app.winfo_width() - w) // 2
    y = app.winfo_rooty() + (app.winfo_height() - h) // 2
    dlg.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
    dlg.after(120, dlg.grab_set)
    dlg.after(10, dlg.lift)
    frame = ctk.CTkFrame(dlg, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=22, pady=22)
    dlg.bind("<Escape>", lambda e: dlg.destroy())
    return dlg, frame


def dialog_buttons(frame, dlg, ok_cmd, ok_text="✓  Enregistrer", color=BLUE, hover=BLUE_D):
    bar = ctk.CTkFrame(frame, fg_color="transparent")
    bar.pack(fill="x", side="bottom", pady=(14, 0))
    ctk.CTkButton(bar, text="Annuler", command=dlg.destroy, fg_color=SLATE,
                  hover_color=SLATE_D, width=100).pack(side="right", padx=(8, 0))
    ctk.CTkButton(bar, text=ok_text, command=ok_cmd, fg_color=color,
                  hover_color=hover, width=150).pack(side="right")
    return bar
