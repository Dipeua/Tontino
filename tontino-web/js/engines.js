/* engines.js — un "moteur" par type de tontine (rotative, enchères, épargne).
   Chaque moteur dit à l'UI quoi afficher et applique les actions. */
(function (root) {
  const T = (root.Tontino = root.Tontino || {});
  const M = T; // helpers du modèle sont sur le même namespace
  const f = T.fmtMoney;

  function current(t) { const r = M.restants(t); return r[0] || null; }
  function upcoming(t) { const r = M.restants(t); return r[1] || null; }

  /* ---------------- ROTATIVE ---------------- */
  const rotative = {
    id: "rotative", label: T.TYPES.rotative, usesPenalties: true,
    current, upcoming,
    canDraw: (t) => t.ordre === "tirage",
    draw(t) {
      const idx = [];
      t.membres.forEach((m, i) => { if (!m.recu) idx.push(i); });
      if (idx.length < 2) return false;
      const rest = idx.map((i) => t.membres[i]);
      for (let i = rest.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [rest[i], rest[j]] = [rest[j], rest[i]];
      }
      idx.forEach((i, pos) => (t.membres[i] = rest[pos]));
      return true;
    },
    cards(t) {
      const cur = current(t), nxt = upcoming(t), cag = M.cagnotte(t);
      let pv, ps;
      if (cur) { pv = cur.nom; ps = "reçoit " + f(cag); }
      else if (!t.membres.length) { pv = "— aucun membre —"; ps = ""; }
      else { pv = "Cycle terminé 🎉"; ps = "lancez un nouveau cycle"; }
      return {
        primary: { label: "🍽 BOUFFE MAINTENANT", value: pv, sub: ps },
        secondary: { label: "⏭ PROCHAIN À BOUFFER", value: nxt ? nxt.nom : "—", sub: "à la prochaine séance" },
        action: { label: "✓ Valider la séance", key: "validate" },
        extra: [], canDraw: t.ordre === "tirage",
      };
    },
    stats(t) {
      const n = t.membres.length, r = t.membres.filter((m) => m.recu).length;
      return [
        ["CYCLE · TOUR", `Cycle ${t.cycle} · Tour ${t.tour}`],
        ["CAGNOTTE DU TOUR", f(M.cagnotte(t))],
        ["ONT BOUFFÉ", n ? `${r} / ${n}` : "—"],
        ["CAISSE (ÉPARGNE)", f(t.caisse)],
      ];
    },
    headers: () => ["Statut", "Cotisation", "Pénalités"],
    row(t, m) {
      const cur = current(t), nxt = upcoming(t);
      let statut, tag = "";
      if (m.recu) { statut = "✓ A bouffé" + (m.date_recu ? " · " + m.date_recu : ""); tag = "done"; }
      else if (m === cur) { statut = "🍽 Bouffe maintenant"; tag = "cur"; }
      else if (m === nxt) { statut = "⏭ Prochain"; tag = "next"; }
      else statut = "En attente";
      const pen = M.penaliteMembre(t, m);
      return { statut, tag, info1: m.seance.cotise ? "✓ Payé" : "—", info2: pen ? f(pen) : "—" };
    },
    validate(t, p) {
      const b = M.restants(t).find((m) => m.nom === p.beneficiaire);
      if (!b) return null;
      const cag = M.cagnotte(t), pen = M.penalitesSeance(t), details = M.detailsPenalites(t);
      b.recu = true; b.date_recu = p.date;
      t.caisse += pen;
      const s = { cycle: t.cycle, tour: t.tour, date: p.date, beneficiaire: b.nom, montant: cag, penalites: pen, mise: 0, type: "rotative", details };
      t.historique.push(s); t.tour += 1; M.resetSeances(t);
      return s;
    },
    newCycle(t) {
      t.membres.forEach((m) => { m.recu = false; m.date_recu = null; m.seance = M.seanceVierge(); });
      t.tour = 1; t.cycle += 1;
    },
  };

  /* ---------------- ENCHÈRES ---------------- */
  function dernierGagnant(t) {
    for (let i = t.historique.length - 1; i >= 0; i--) if (t.historique[i].type === "encheres") return t.historique[i];
    return null;
  }
  const encheres = {
    id: "encheres", label: T.TYPES.encheres, usesPenalties: true,
    current: () => null, upcoming: () => null, canDraw: () => false, draw: () => false,
    cards(t) {
      const cag = M.cagnotte(t), d = dernierGagnant(t), rest = M.restants(t);
      let pv, ps;
      if (!rest.length) { pv = t.membres.length ? "Cycle terminé 🎉" : "— aucun membre —"; ps = t.membres.length ? "lancez un nouveau cycle" : ""; }
      else { pv = "À adjuger"; ps = `cagnotte ${f(cag)} · ${rest.length} en lice`; }
      return {
        primary: { label: "🔨 ENCHÈRE EN COURS", value: pv, sub: ps },
        secondary: { label: "🏆 DERNIER GAGNANT", value: d ? d.beneficiaire : "—", sub: d ? `mise ${f(d.mise)} · ${d.date}` : "aucune enchère" },
        action: { label: "🔨 Adjuger l'enchère", key: "enchere" },
        extra: [], canDraw: false,
      };
    },
    stats(t) {
      const n = t.membres.length, r = t.membres.filter((m) => m.recu).length;
      return [
        ["CYCLE · TOUR", `Cycle ${t.cycle} · Tour ${t.tour}`],
        ["CAGNOTTE", f(M.cagnotte(t))],
        ["ONT GAGNÉ", n ? `${r} / ${n}` : "—"],
        ["CAISSE (MISES)", f(t.caisse)],
      ];
    },
    headers: () => ["Statut", "Cotisation", "Pénalités"],
    row(t, m) {
      let statut, tag = "";
      if (m.recu) { statut = "🏆 A remporté" + (m.date_recu ? " · " + m.date_recu : ""); tag = "done"; }
      else statut = "En lice";
      const pen = M.penaliteMembre(t, m);
      return { statut, tag, info1: m.seance.cotise ? "✓ Payé" : "—", info2: pen ? f(pen) : "—" };
    },
    validate(t, p) {
      const b = M.restants(t).find((m) => m.nom === p.beneficiaire);
      if (!b) return null;
      const cag = M.cagnotte(t), pen = M.penalitesSeance(t), details = M.detailsPenalites(t), mise = p.mise || 0;
      b.recu = true; b.date_recu = p.date;
      t.caisse += pen + mise;
      const s = { cycle: t.cycle, tour: t.tour, date: p.date, beneficiaire: b.nom, montant: cag, penalites: pen, mise, type: "encheres", details };
      t.historique.push(s); t.tour += 1; M.resetSeances(t);
      return s;
    },
    newCycle: rotative.newCycle,
  };

  /* ---------------- ÉPARGNE ---------------- */
  const epargne = {
    id: "epargne", label: T.TYPES.epargne, usesPenalties: false,
    current: () => null, upcoming: () => null, canDraw: () => false, draw: () => false,
    cards(t) {
      const nb = t.historique.filter((s) => s.type === "epargne_depot").length;
      return {
        primary: { label: "🏦 FONDS ÉPARGNÉ", value: f(t.fonds), sub: `${nb} séance(s) de collecte` },
        secondary: { label: "📤 DISTRIBUTION", value: "en fin de cycle", sub: `${t.membres.length} membre(s)` },
        action: { label: "💰 Encaisser une séance", key: "epargne" },
        extra: [{ label: "📤 Distribuer le fonds", key: "distribute" }], canDraw: false,
      };
    },
    stats(t) {
      const n = t.membres.length, moy = n ? Math.floor(t.fonds / n) : 0;
      return [
        ["CYCLE · SÉANCE", `Cycle ${t.cycle} · Séance ${t.tour}`],
        ["FONDS TOTAL", f(t.fonds)],
        ["MEMBRES", String(n)],
        ["MOYENNE / MEMBRE", f(moy)],
      ];
    },
    headers: () => ["Épargne totale", "Dernier dépôt", ""],
    row(t, m) {
      let dernier = 0;
      for (let i = t.historique.length - 1; i >= 0; i--) {
        const s = t.historique[i];
        if (s.type === "epargne_depot") {
          const d = (s.details || []).find((x) => x.nom === m.nom);
          if (d) dernier = d.montant;
          break;
        }
      }
      return { statut: f(m.epargne), tag: "", info1: dernier ? f(dernier) : "—", info2: "" };
    },
    collect(t, p) {
      let total = 0; const details = [];
      t.membres.forEach((m) => {
        const montant = parseInt((p.depots || {})[m.id], 10) || 0;
        if (montant) { m.epargne += montant; total += montant; details.push({ nom: m.nom, montant }); }
      });
      t.fonds += total;
      const s = { cycle: t.cycle, tour: t.tour, date: p.date, beneficiaire: "(collecte épargne)", montant: total, penalites: 0, mise: 0, type: "epargne_depot", details };
      t.historique.push(s); t.tour += 1;
      return s;
    },
    distribute(t, p) {
      if (t.fonds <= 0 || !t.membres.length) return null;
      const n = t.membres.length, details = [];
      if (p.mode === "prorata") {
        const base = t.membres.reduce((s, m) => s + m.epargne, 0) || 1;
        t.membres.forEach((m) => details.push({ nom: m.nom, montant: Math.round(t.fonds * m.epargne / base) }));
      } else {
        const part = Math.floor(t.fonds / n);
        t.membres.forEach((m) => details.push({ nom: m.nom, montant: part }));
      }
      const s = { cycle: t.cycle, tour: t.tour, date: p.date, beneficiaire: "DISTRIBUTION", montant: t.fonds, penalites: 0, mise: 0, type: "epargne_distrib", details };
      t.historique.push(s);
      t.fonds = 0; t.membres.forEach((m) => (m.epargne = 0)); t.cycle += 1; t.tour = 1;
      return s;
    },
    newCycle(t) {
      t.fonds = 0;
      t.membres.forEach((m) => { m.epargne = 0; m.recu = false; m.date_recu = null; });
      t.tour = 1; t.cycle += 1;
    },
  };

  T.ENGINES = { rotative, encheres, epargne };
  T.getEngine = (id) => T.ENGINES[id] || rotative;
})(typeof window !== "undefined" ? window : globalThis);
