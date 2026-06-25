/* print.js — génère un relevé imprimable (style facture) puis ouvre l'impression.
   L'utilisateur peut « Enregistrer au format PDF » depuis la boîte d'impression. */
(function (root) {
  const T = (root.Tontino = root.Tontino || {});
  const f = T.fmtMoney;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  function rows(arr) { return arr.map((r) => "<tr>" + r.map((c, i) => `<td class="${i >= r.length - 1 ? 'num' : ''}">${esc(c)}</td>`).join("") + "</tr>").join(""); }

  T.printDoc = function (t, engine) {
    const PR = document.getElementById("print-root");
    const cur = engine.current(t), nxt = engine.upcoming(t);
    const recu = t.membres.filter((m) => m.recu).length;
    let meta;
    if (t.type === "epargne") {
      meta = `
        <div class="meta">
          <div><span>Type</span><b>${esc(T.TYPES[t.type])}</b></div>
          <div><span>Fonds épargné</span><b>${f(t.fonds)}</b></div>
          <div><span>Membres</span><b>${t.membres.length}</b></div>
          <div><span>Moyenne / membre</span><b>${f(t.membres.length ? Math.floor(t.fonds / t.membres.length) : 0)}</b></div>
        </div>`;
    } else {
      const labelCaisse = t.type === "encheres" ? "Caisse (mises)" : "Caisse (épargne)";
      meta = `
        <div class="meta">
          <div><span>Cotisation / membre</span><b>${f(t.cotisation)}</b></div>
          <div><span>Cagnotte du tour</span><b>${f(T.cagnotte(t))}</b></div>
          <div><span>Membres</span><b>${t.membres.length}</b></div>
          <div><span>${labelCaisse}</span><b>${f(t.caisse)}</b></div>
          <div><span>Ont bénéficié</span><b>${recu} / ${t.membres.length}</b></div>
          <div><span>En cours / prochain</span><b>${esc(cur ? cur.nom : "—")} / ${esc(nxt ? nxt.nom : "—")}</b></div>
        </div>`;
    }

    // Tableau des membres
    let memRows;
    if (t.type === "epargne") {
      memRows = t.membres.map((m, i) => [i + 1, m.nom, m.tel, f(m.epargne)]);
      var memHead = ["#", "Membre", "Téléphone", "Épargne totale"];
    } else {
      memHead = ["#", "Membre", "Téléphone", "Statut"];
      memRows = t.membres.map((m, i) => {
        let st;
        if (t.type === "encheres") st = m.recu ? "A remporté" + (m.date_recu ? " le " + m.date_recu : "") : "En lice";
        else st = m.recu ? "A bouffé" + (m.date_recu ? " le " + m.date_recu : "") : (m === cur ? "Bouffe maintenant" : (m === nxt ? "Prochain" : "En attente"));
        return [i + 1, m.nom, m.tel, st];
      });
    }

    // Historique
    let histHtml = "";
    if (t.historique.length) {
      let hh, hr;
      if (t.type === "epargne") {
        hh = ["Cycle", "Séance", "Date", "Opération", "Montant"];
        hr = t.historique.map((s) => [s.cycle, s.tour, s.date, s.type === "epargne_distrib" ? "Distribution" : "Collecte", f(s.montant)]);
      } else {
        hh = ["Cycle", "Tour", "Date", "Bénéficiaire", "Cagnotte", t.type === "encheres" ? "Mise" : "Pénalités"];
        hr = t.historique.map((s) => [s.cycle, s.tour, s.date, s.beneficiaire, f(s.montant), f(t.type === "encheres" ? s.mise : s.penalites)]);
      }
      histHtml = `<h2>Historique des séances</h2><table><thead><tr>${hh.map((x, i) => `<th class="${i >= hh.length - 1 ? 'num' : ''}">${x}</th>`).join("")}</tr></thead><tbody>${rows(hr)}</tbody></table>`;
    }

    PR.innerHTML = `
      <div class="pdoc">
        <div class="phead">
          <div class="ptitle">${esc(t.nom)}</div>
          <div class="pright">${esc(T.TYPES[t.type])}<br>${new Date().toLocaleString("fr-FR")}<br>Cycle ${t.cycle} · Tour ${t.tour}</div>
        </div>
        ${meta}
        <h2>Membres</h2>
        <table><thead><tr>${memHead.map((x, i) => `<th class="${i === memHead.length - 1 && t.type === "epargne" ? 'num' : ''}">${x}</th>`).join("")}</tr></thead><tbody>${rows(memRows)}</tbody></table>
        ${histHtml}
        <div class="pfoot">Tontino-Web — document généré automatiquement.</div>
      </div>`;
    window.print();
  };
})(typeof window !== "undefined" ? window : globalThis);
