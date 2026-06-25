"""Thème CustomTkinter + style du tableau (ttk.Treeview) selon clair/sombre."""

import customtkinter as ctk

from ..config import BLUE


def setup():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


def _palette():
    if ctk.get_appearance_mode() == "Dark":
        return dict(bg="#2b2b2b", fg="#dce4ee", head="#212121", head_fg="#94a3b8",
                    odd="#2b2b2b", even="#333333", cur="#14532d", nxt="#1e3a5f",
                    done_fg="#7f8c9b", done_bg="#242424")
    return dict(bg="#ffffff", fg="#1e293b", head="#eef2f7", head_fg="#64748b",
                odd="#ffffff", even="#f5f8fc", cur="#dcfce7", nxt="#dbeafe",
                done_fg="#94a3b8", done_bg="#eef1f5")


def style_tree(style, tree):
    c = _palette()
    style.theme_use("clam")
    style.configure("Treeview", background=c["bg"], fieldbackground=c["bg"],
                    foreground=c["fg"], rowheight=36, borderwidth=0, font=("Segoe UI", 10))
    style.configure("Treeview.Heading", background=c["head"], foreground=c["head_fg"],
                    font=("Segoe UI Semibold", 10), relief="flat", padding=8)
    style.map("Treeview.Heading", background=[("active", c["head"])])
    style.map("Treeview", background=[("selected", BLUE)], foreground=[("selected", "#ffffff")])
    tree.tag_configure("odd", background=c["odd"], foreground=c["fg"])
    tree.tag_configure("even", background=c["even"], foreground=c["fg"])
    tree.tag_configure("cur", background=c["cur"])
    tree.tag_configure("next", background=c["nxt"])
    tree.tag_configure("done", foreground=c["done_fg"], background=c["done_bg"])
