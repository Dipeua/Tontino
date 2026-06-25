/* ui.js — rendu du DOM, système de fenêtres modales et tous les dialogues. */
(function (root) {
  const T = (root.Tontino = root.Tontino || {});
  const f = T.fmtMoney;
  const ui = (T.ui = {});

  /* ---------- Helpers DOM ---------- */
  function el(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === "class") e.className = attrs[k];
      else if (k === "html") e.innerHTML = attrs[k];
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] != null) e.setAttribute(k, attrs[k]);
    }
    kids.flat().forEach((c) => { if (c != null) e.append(c.nodeType ? c : document.createTextNode(c)); });
    return e;
  }
  ui.el = el;
  const $ = (id) => document.getElementById(id);

  /* ---------- Modale ---------- */
  function modal(title, width) {
    const root = $("modal-root");
    const overlay = el("div", { class: "overlay" });
    const card = el("div", { class: "modal" });
    if (width) card.style.maxWidth = width + "px";
    const head = el("div", { class: "modal-head" }, el("h3", null, title),
      el("button", { class: "x", onclick: close }, "✕"));
    const body = el("div", { class: "modal-body" });
    const foot = el("div", { class: "modal-foot" });
    card.append(head, body, foot);
    overlay.append(card);
    overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
    function esc(e) { if (e.key === "Escape") close(); }
    document.addEventListener("keydown", esc);
    function close() { overlay.remove(); document.removeEventListener("keydown", esc); }
    root.append(overlay);
    return { body, foot, close };
  }

  function field(parent, label, input) {
    parent.append(el("label", { class: "fld" }, el("span", null, label), input));
    return input;
  }
  function input(value, ph) { return el("input", { class: "in", value: value == null ? "" : value, placeholder: ph || "" }); }
  function select(options, value) {
    const s = el("select", { class: "in" });
    options.forEach(([v, lab]) => { const o = el("option", { value: v }, lab); if (v === value) o.selected = true; s.append(o); });
    return s;
  }
  function segmented(options, value) {
    const wrap = el("div", { class: "seg" });
    let cur = value;
    const btns = {};
    options.forEach(([v, lab]) => {
      const b = el("button", { type: "button", class: "seg-b" + (v === value ? " on" : ""),
        onclick: () => { cur = v; Object.values(btns).forEach((x) => x.classList.remove("on")); b.classList.add("on"); } }, lab);
      btns[v] = b; wrap.append(b);
    });
    wrap.get = () => cur;
    return wrap;
  }
  function footBtns(m, okLabel, okFn, okClass) {
    m.foot.append(
      el("button", { class: "btn ghost", onclick: m.close }, "Annuler"),
      el("button", { class: "btn " + (okClass || "primary"), onclick: okFn }, okLabel)
    );
  }

  /* ---------- Rendu principal ---------- */
  ui.render = function (ctx) {
    const t = ctx.t, e = ctx.engine;
    const ordreTxt = t.type === "rotative" ? " · " + T.ORDRES[t.ordre] : "";
    $("subtitle").textContent = `${t.nom}  ·  ${T.TYPES[t.type]}${ordreTxt}`;

    const c = e.cards(t);
    $("curLabel").textContent = c.primary.label;
    $("curValue").textContent = c.primary.value;
    $("curSub").textContent = c.primary.sub;
    $("nxtLabel").textContent = c.secondary.label;
    $("nxtValue").textContent = c.secondary.value;
    $("nxtSub").textContent = c.secondary.sub;

    const bp = $("btnPrimary");
    bp.textContent = c.action.label;
    bp.onclick = () => ui.openAction(ctx, c.action.key);
    const bd = $("btnDraw");
    bd.style.display = c.canDraw ? "" : "none";
    bd.onclick = () => ctx.draw();
    const bx = $("btnExtra");
    if (c.extra && c.extra.length) {
      bx.style.display = ""; bx.textContent = c.extra[0].label;
      bx.onclick = () => ui.openAction(ctx, c.extra[0].key);
    } else bx.style.display = "none";

    // stats
    const sc = $("stats"); sc.innerHTML = "";
    e.stats(t).forEach(([lab, val]) => {
      sc.append(el("div", { class: "chip" }, el("div", { class: "chip-l" }, lab), el("div", { class: "chip-v" }, val)));
    });

    // bouton pointer
    $("btnPointage").disabled = !e.usesPenalties;

    // en-têtes tableau
    const h = e.headers();
    $("hStatut").textContent = h[0];
    $("hInfo1").textContent = h[1];
    $("hInfo2").textContent = h[2];

    // lignes
    const tb = $("tbody"); tb.innerHTML = "";
    t.membres.forEach((m, i) => {
      const r = e.row(t, m);
      const tr = el("tr", { class: (r.tag ? "row-" + r.tag : "") + (m.id === ctx.selectedId ? " sel" : "") });
      tr.append(el("td", { class: "c" }, String(i + 1)), el("td", null, m.nom), el("td", null, m.tel || "—"),
        el("td", null, r.statut), el("td", { class: "c" }, r.info1), el("td", { class: "num" }, r.info2));
      tr.addEventListener("click", () => { ctx.selectedId = m.id; ui.render(ctx); });
      tr.addEventListener("dblclick", () => { ctx.selectedId = m.id; ui.dlgPointage(ctx); });
      tb.append(tr);
    });
  };

  ui.openAction = function (ctx, key) {
    ({ validate: ui.dlgRotative, enchere: ui.dlgEnchere, epargne: ui.dlgEpargne, distribute: ui.dlgDistribute }[key] || (() => {}))(ctx);
  };

  function selected(ctx) {
    const m = ctx.t.membres.find((x) => x.id === ctx.selectedId);
    if (!m) ctx.setStatus("Sélectionnez un membre.", "danger");
    return m;
  }
  ui.selected = selected;

  /* ---------- Dialogues : membre ---------- */
  ui.dlgEditMember = function (ctx) {
    const m = selected(ctx); if (!m) return;
    const md = modal("Modifier le membre", 440);
    const nom = field(md.body, "Nom", input(m.nom));
    const tel = field(md.body, "Téléphone", input(m.tel));
    footBtns(md, "✓ Enregistrer", () => {
      if (!nom.value.trim()) return alert("Le nom est vide.");
      m.nom = nom.value.trim(); m.tel = tel.value.trim();
      ctx.commit(); md.close();
    });
    nom.focus();
  };

  ui.dlgPointage = function (ctx) {
    if (!ctx.engine.usesPenalties) { ctx.setStatus("Pas de pénalités pour ce type.", "warn"); return; }
    const m = selected(ctx); if (!m) return;
    const t = ctx.t, s = m.seance, p = t.penalites;
    const md = modal("Pointage — " + m.nom, 460);
    const pres = segmented([["present", "Présent"], ["absent", `Absent (+${p.absence})`]], s.presence || "present");
    md.body.append(el("div", { class: "fld" }, el("span", null, "Présence"), pres));
    const mk = (key, label) => {
      const cb = el("input", { type: "checkbox" }); cb.checked = !!s[key];
      cb.addEventListener("change", recompute);
      md.body.append(el("label", { class: "chk" }, cb, label));
      return cb;
    };
    const cot = mk("cotise", `A payé sa cotisation (${f(t.cotisation)})`);
    md.body.append(el("div", { class: "muted small" }, "Pénalités :"));
    const rp = mk("retard_physique", `Retard physique (+${p.retard_physique})`);
    const rc = mk("retard_cotisation", `Retard cotisation (+${p.retard_cotisation})`);
    const ec = mk("echec_cotisation", `Échec cotisation (+${p.echec_cotisation})`);
    const tot = el("div", { class: "total" });
    md.body.append(tot);
    pres.querySelectorAll("button").forEach((b) => b.addEventListener("click", recompute));
    function recompute() {
      let x = 0;
      if (pres.get() === "absent") x += p.absence;
      if (rp.checked) x += p.retard_physique;
      if (rc.checked) x += p.retard_cotisation;
      if (ec.checked) x += p.echec_cotisation;
      tot.textContent = "Pénalités → caisse : " + f(x);
    }
    recompute();
    footBtns(md, "✓ Enregistrer", () => {
      s.presence = pres.get(); s.cotise = cot.checked; s.retard_physique = rp.checked;
      s.retard_cotisation = rc.checked; s.echec_cotisation = ec.checked;
      ctx.commit(); md.close();
    });
  };

  /* ---------- Dialogues : réglages ---------- */
  ui.dlgSettings = function (ctx) {
    const t = ctx.t;
    const md = modal("Réglages de la tontine", 480);
    const nom = field(md.body, "Nom de la tontine", input(t.nom));
    const type = field(md.body, "Type de tontine", select(Object.entries(T.TYPES), t.type));
    const ordre = segmented([["fixe", T.ORDRES.fixe], ["tirage", T.ORDRES.tirage]], t.ordre);
    md.body.append(el("div", { class: "fld" }, el("span", null, "Ordre de passage (rotative)"), ordre));
    const cot = field(md.body, "Cotisation par membre / séance (FCFA)", input(t.cotisation));
    md.body.append(el("div", { class: "muted small" }, "Pénalités (→ caisse)"));
    const pv = {};
    Object.keys(T.PENALITES_DEFAUT).forEach((k) => {
      const ip = input(t.penalites[k]); ip.style.maxWidth = "130px"; pv[k] = ip;
      md.body.append(el("div", { class: "fld-row" }, el("span", null, T.PENALITES_LABELS[k]), ip));
    });
    footBtns(md, "✓ Enregistrer", () => {
      t.nom = nom.value.trim() || "Ma tontine";
      t.type = type.value; t.ordre = ordre.get(); t.cotisation = T.parseInt(cot.value);
      Object.keys(pv).forEach((k) => (t.penalites[k] = T.parseInt(pv[k].value)));
      ctx.reloadEngine(); ctx.commit(); md.close();
    });
  };

  /* ---------- Dialogues : séances ---------- */
  function dateField(body, label) {
    return field(body, label || "Date de la séance (jj/mm/aaaa)", input(T.today()));
  }

  ui.dlgRotative = function (ctx) {
    const t = ctx.t, e = ctx.engine, rest = T.restants(t);
    if (!rest.length) return alert(t.membres.length ? "Tout le monde a bénéficié. Lancez un nouveau cycle." : "Ajoutez des membres.");
    const md = modal("Valider la séance", 470);
    const cur = e.current(t);
    const who = field(md.body, "🍽 Qui bouffe (reçoit la cagnotte) ?", select(rest.map((m) => [m.nom, m.nom]), cur ? cur.nom : rest[0].nom));
    md.body.append(el("div", { class: "muted small" }, `💰 Cagnotte : ${f(T.cagnotte(t))}  ·  🏦 Pénalités : ${f(T.penalitesSeance(t))}`));
    const d = dateField(md.body);
    footBtns(md, "✓ Valider", () => {
      e.validate(t, { beneficiaire: who.value, date: d.value.trim() || T.today() });
      ctx.commit(); md.close();
    }, "ok");
  };

  ui.dlgEnchere = function (ctx) {
    const t = ctx.t, e = ctx.engine, rest = T.restants(t);
    if (!rest.length) return alert(t.membres.length ? "Tout le monde a gagné. Lancez un nouveau cycle." : "Ajoutez des membres.");
    const md = modal("Adjuger l'enchère", 470);
    const who = field(md.body, "🏆 Qui remporte (plus offrant) ?", select(rest.map((m) => [m.nom, m.nom]), rest[0].nom));
    const mise = field(md.body, "Montant de la mise gagnante (→ caisse, FCFA)", input(0));
    md.body.append(el("div", { class: "muted small" }, `💰 Cagnotte remportée : ${f(T.cagnotte(t))}`));
    const d = dateField(md.body);
    footBtns(md, "🔨 Adjuger", () => {
      e.validate(t, { beneficiaire: who.value, date: d.value.trim() || T.today(), mise: T.parseInt(mise.value) });
      ctx.commit(); md.close();
    }, "ok");
  };

  ui.dlgEpargne = function (ctx) {
    const t = ctx.t, e = ctx.engine;
    if (!t.membres.length) return alert("Ajoutez des membres.");
    const md = modal("Encaisser une séance d'épargne", 480);
    md.body.append(el("div", { class: "muted small" }, "Montant déposé par chaque membre (FCFA) :"));
    const box = el("div", { class: "deposit-list" });
    const fields = {};
    t.membres.forEach((m) => {
      const ip = input(t.cotisation); ip.style.maxWidth = "140px"; fields[m.id] = ip;
      box.append(el("div", { class: "fld-row" }, el("span", null, m.nom), ip));
    });
    md.body.append(box);
    const d = dateField(md.body);
    footBtns(md, "💰 Encaisser", () => {
      const depots = {}; Object.keys(fields).forEach((id) => (depots[id] = T.parseInt(fields[id].value)));
      const s = e.collect(t, { depots, date: d.value.trim() || T.today() });
      ctx.setStatus("Collecte : " + f(s.montant) + " encaissés.", "ok");
      ctx.commit(); md.close();
    }, "ok");
  };

  ui.dlgDistribute = function (ctx) {
    const t = ctx.t, e = ctx.engine;
    if (t.fonds <= 0) return alert("Il n'y a rien à distribuer.");
    const md = modal("Distribuer le fonds", 460);
    md.body.append(el("div", { class: "muted" }, `Fonds à distribuer : ${f(t.fonds)} · ${t.membres.length} membre(s)`));
    const mode = segmented([["egal", "À parts égales"], ["prorata", "Au prorata de l'épargne"]], "egal");
    md.body.append(el("div", { class: "fld" }, el("span", null, "Mode de répartition"), mode));
    const d = dateField(md.body, "Date de la distribution");
    md.body.append(el("div", { class: "warn-note" }, "⚠ Cela clôture le cycle (fonds et épargnes remis à zéro)."));
    footBtns(md, "📤 Distribuer", () => {
      e.distribute(t, { mode: mode.get(), date: d.value.trim() || T.today() });
      ctx.commit(); md.close();
    }, "ok");
  };

  /* ---------- Dialogue : historique ---------- */
  ui.dlgHistory = function (ctx) {
    const t = ctx.t;
    const md = modal("Historique des séances", 760);
    const info = el("div", { class: "hist-info" });
    md.body.append(info);
    if (t.type === "rotative" || t.type === "encheres") {
      md.body.append(el("button", { class: "btn ok", onclick: () => { (t.type === "encheres" ? ui.dlgEnchere : ui.dlgRotative)(ctx); md.close(); ui.dlgHistory(ctx); } }, "➕ Ajouter une séance"));
    }
    const list = el("div", { class: "hist-list" });
    md.body.append(list);
    function build() {
      info.textContent = t.type === "epargne"
        ? `Fonds : ${f(t.fonds)} · Cycle ${t.cycle} · Séance ${t.tour}`
        : `Caisse : ${f(t.caisse)} · Cycle ${t.cycle} · Tour ${t.tour}`;
      list.innerHTML = "";
      if (!t.historique.length) { list.append(el("div", { class: "muted" }, "Aucune séance enregistrée.")); return; }
      t.historique.forEach((s, idx) => {
        let txt;
        if (s.type && s.type.startsWith("epargne")) {
          txt = `Cycle ${s.cycle} · Séance ${s.tour} · ${s.date} · ${s.type === "epargne_distrib" ? "Distribution" : "Collecte"} : ${f(s.montant)}`;
        } else if (s.type === "encheres") {
          txt = `Cycle ${s.cycle} · Tour ${s.tour} · ${s.date} · 🏆 ${s.beneficiaire} · ${f(s.montant)} · mise ${f(s.mise)}`;
        } else {
          txt = `Cycle ${s.cycle} · Tour ${s.tour} · ${s.date} · ${s.beneficiaire} · ${f(s.montant)} · pénal. ${f(s.penalites)}`;
        }
        const row = el("div", { class: "hist-row" }, el("span", null, txt),
          el("button", { class: "btn danger mini", onclick: () => delSession(idx) }, "🗑"));
        list.append(row);
        (s.details || []).forEach((d) => {
          const line = "motifs" in d ? `⤷ ${d.nom} : ${(d.motifs || []).join(", ")} — ${f(d.montant)}`
            : `⤷ ${d.nom} : ${f(d.montant)}`;
          list.append(el("div", { class: "hist-detail" }, line));
        });
      });
    }
    function delSession(idx) {
      const s = t.historique[idx];
      if (s.type === "epargne_distrib") return alert("Une distribution ne peut pas être annulée ici.");
      if (!confirm("Supprimer cette séance du " + s.date + " ?")) return;
      if (s.type === "epargne_depot") {
        t.fonds = Math.max(0, t.fonds - s.montant);
        (s.details || []).forEach((d) => { const m = t.membres.find((x) => x.nom === d.nom); if (m) m.epargne = Math.max(0, m.epargne - d.montant); });
        if (s.cycle === t.cycle) t.tour = Math.max(1, t.tour - 1);
      } else {
        t.caisse = Math.max(0, t.caisse - s.penalites - s.mise);
        if (s.cycle === t.cycle) {
          const m = t.membres.find((x) => x.nom === s.beneficiaire);
          if (m && m.recu && (m.date_recu === s.date || !s.date)) { m.recu = false; m.date_recu = null; }
          t.tour = Math.max(1, t.tour - 1);
        }
      }
      t.historique.splice(idx, 1);
      ctx.save(); ctx.refresh(); build();
    }
    build();
    md.foot.append(el("button", { class: "btn primary", onclick: md.close }, "Fermer"));
  };
})(typeof window !== "undefined" ? window : globalThis);
