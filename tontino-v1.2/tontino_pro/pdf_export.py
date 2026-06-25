"""Export PDF style « facture » (sobre), adapté au type de tontine."""

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from .config import APP_NAME, TYPES
from .utils import fmt_money

INK = colors.HexColor("#111827")
SOFT = colors.HexColor("#6b7280")
LINE = colors.HexColor("#d1d5db")
HEAD = colors.HexColor("#1f2937")
ALT = colors.HexColor("#f9fafb")
MARK = colors.HexColor("#fef3c7")


def _hstyle(extra=None):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALT]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE)] + (extra or []))


def _statut_rotative(t, engine, m):
    if m.recu:
        return "A bouffé" + (f" le {m.date_recu}" if m.date_recu else "")
    if m is engine.current(t):
        return "Bouffe maintenant"
    if m is engine.upcoming(t):
        return "Prochain à bouffer"
    return "En attente"


def export(t, engine, path):
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm, title=t.nom)
    S = getSampleStyleSheet()
    st_title = ParagraphStyle("t", parent=S["Normal"], fontSize=22, textColor=INK,
                              leading=24, fontName="Helvetica-Bold")
    st_right = ParagraphStyle("r", parent=S["Normal"], fontSize=10, textColor=SOFT, alignment=2)
    st_soft = ParagraphStyle("s", parent=S["Normal"], fontSize=9, textColor=SOFT)
    st_h2 = ParagraphStyle("h", parent=S["Normal"], fontSize=12, textColor=INK,
                           fontName="Helvetica-Bold", spaceAfter=4)
    PW = 17.4 * cm

    ent = Table([[Paragraph(t.nom, st_title),
                  Paragraph(f"{TYPES.get(t.type, t.type)}<br/>{datetime.now():%d/%m/%Y à %H:%M}<br/>"
                            f"Cycle {t.cycle} · Tour {t.tour}", st_right)]],
                colWidths=[PW * 0.58, PW * 0.42])
    ent.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                             ("LINEBELOW", (0, 0), (-1, -1), 1.0, INK),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story = [ent, Spacer(1, 0.35 * cm)]

    # --- Bloc méta selon le type ---
    if t.type == "epargne":
        meta_rows = [
            ["Type", TYPES.get(t.type, t.type), "Fonds épargné", fmt_money(t.fonds)],
            ["Membres", str(len(t.membres)), "Moyenne / membre",
             fmt_money(t.fonds // len(t.membres)) if t.membres else "0 FCFA"],
        ]
    else:
        cur, nxt = engine.current(t), engine.upcoming(t)
        recu = sum(1 for m in t.membres if m.recu)
        label_caisse = "Caisse (mises)" if t.type == "encheres" else "Caisse (épargne)"
        meta_rows = [
            ["Cotisation / membre", fmt_money(t.cotisation), "Cagnotte du tour", fmt_money(t.cagnotte())],
            ["Membres", str(len(t.membres)), label_caisse, fmt_money(t.caisse)],
            ["Ont bénéficié", f"{recu} / {len(t.membres)}",
             "Bénéficiaire en cours", cur.nom if cur else "—"],
            ["", "", "Prochain", nxt.nom if nxt else "—"],
        ]
    meta = Table(meta_rows, colWidths=[PW * 0.25, PW * 0.25, PW * 0.27, PW * 0.23])
    meta.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"), ("FONTNAME", (2, 0), (2, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 0), (0, -1), SOFT), ("TEXTCOLOR", (2, 0), (2, -1), SOFT),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"), ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 0), (1, -1), INK), ("TEXTCOLOR", (3, 0), (3, -1), INK),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5), ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [meta, Spacer(1, 0.5 * cm), Paragraph("Membres", st_h2)]

    # --- Table des membres ---
    if t.type == "epargne":
        data = [["#", "Membre", "Téléphone", "Épargne totale"]]
        for i, m in enumerate(t.membres, 1):
            data.append([str(i), m.nom, m.tel, fmt_money(m.epargne)])
        col = [1.0 * cm, 6.4 * cm, 4.0 * cm, 6.0 * cm]
        extra = [("ALIGN", (0, 0), (0, -1), "CENTER"), ("ALIGN", (3, 0), (3, -1), "RIGHT")]
    else:
        data = [["#", "Membre", "Téléphone", "Statut"]]
        for i, m in enumerate(t.membres, 1):
            if t.type == "encheres":
                stt = ("A remporté" + (f" le {m.date_recu}" if m.date_recu else "")) if m.recu else "En lice"
            else:
                stt = _statut_rotative(t, engine, m)
            data.append([str(i), m.nom, m.tel, stt])
        col = [1.0 * cm, 6.4 * cm, 4.0 * cm, 6.0 * cm]
        extra = [("ALIGN", (0, 0), (0, -1), "CENTER")]
    tbl = Table(data, colWidths=col, repeatRows=1)
    tbl.setStyle(_hstyle(extra))
    story.append(tbl)

    # --- Historique ---
    if t.historique:
        story += [Spacer(1, 0.5 * cm), Paragraph("Historique des séances", st_h2)]
        if t.type == "epargne":
            hd = [["Cycle", "Séance", "Date", "Opération", "Montant"]]
            for s in t.historique:
                op = "Distribution" if s.type == "epargne_distrib" else "Collecte"
                hd.append([str(s.cycle), str(s.tour), s.date, op, fmt_money(s.montant)])
            ht = Table(hd, colWidths=[1.6 * cm, 1.8 * cm, 2.8 * cm, 6.7 * cm, 4.5 * cm], repeatRows=1)
            ht.setStyle(_hstyle([("ALIGN", (0, 0), (1, -1), "CENTER"), ("ALIGN", (4, 0), (-1, -1), "RIGHT")]))
        else:
            hd = [["Cycle", "Tour", "Date", "Bénéficiaire", "Cagnotte", "Mise" if t.type == "encheres" else "Pénalités"]]
            for s in t.historique:
                last = s.mise if t.type == "encheres" else s.penalites
                hd.append([str(s.cycle), str(s.tour), s.date, s.beneficiaire,
                           fmt_money(s.montant), fmt_money(last)])
            ht = Table(hd, colWidths=[1.4 * cm, 1.3 * cm, 2.6 * cm, 5.1 * cm, 3.5 * cm, 3.5 * cm], repeatRows=1)
            ht.setStyle(_hstyle([("ALIGN", (0, 0), (1, -1), "CENTER"), ("ALIGN", (4, 0), (-1, -1), "RIGHT")]))
        story.append(ht)

    # --- Détail des pénalités (rotative / enchères) ---
    if t.type != "epargne":
        lp = []
        for s in t.historique:
            for d in s.details:
                if "motifs" in d:
                    lp.append([s.date, d["nom"], ", ".join(d.get("motifs", [])), fmt_money(d["montant"])])
        if lp:
            story += [Spacer(1, 0.5 * cm), Paragraph("Détail des pénalités", st_h2)]
            pd = [["Date", "Membre", "Motif(s)", "Montant"]] + lp
            pd.append(["", "", "Total caisse", fmt_money(t.caisse)])
            pt = Table(pd, colWidths=[2.6 * cm, 4.6 * cm, 6.7 * cm, 3.5 * cm], repeatRows=1)
            pt.setStyle(_hstyle([("ALIGN", (3, 0), (3, -1), "RIGHT"),
                                 ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
                                 ("BACKGROUND", (0, -1), (-1, -1), ALT),
                                 ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK)]))
            story.append(pt)

    story += [Spacer(1, 0.6 * cm),
              Paragraph(f"{APP_NAME} — document généré automatiquement.", st_soft)]
    doc.build(story)
