/* app.js — contrôleur : charge l'état, câble les boutons, orchestre le rendu. */
(function (root) {
  const T = root.Tontino;
  const ui = T.ui;
  const $ = (id) => document.getElementById(id);

  document.addEventListener("DOMContentLoaded", () => {
    // Thème
    const savedTheme = localStorage.getItem("tontino_theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    $("themeBtn").textContent = savedTheme === "dark" ? "🌙" : "☀";

    const ctx = {
      t: T.storage.load(),
      engine: null,
      selectedId: null,
      save() { T.storage.save(this.t); },
      refresh() { ui.render(this); },
      commit() { this.save(); this.refresh(); },
      reloadEngine() { this.engine = T.getEngine(this.t.type); },
      setStatus(msg, type) {
        const s = $("status");
        s.textContent = msg;
        s.className = "status " + (type || "");
      },
      draw() {
        if (!this.engine.canDraw(this.t)) return;
        if (!confirm("Tirer au sort l'ordre des membres qui n'ont pas encore bénéficié ?")) return;
        if (this.engine.draw(this.t)) {
          const c = this.engine.current(this.t);
          this.commit();
          this.setStatus(c ? "🎲 Tirage effectué — " + c.nom + " en premier." : "Tirage effectué.", "ok");
        } else this.setStatus("Pas assez de membres à tirer.", "warn");
      },
    };
    ctx.reloadEngine();

    // --- Boutons globaux ---
    $("settingsBtn").onclick = () => ui.dlgSettings(ctx);
    $("themeBtn").onclick = () => {
      const cur = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", cur);
      localStorage.setItem("tontino_theme", cur);
      $("themeBtn").textContent = cur === "dark" ? "🌙" : "☀";
    };

    // --- Ajout de membre ---
    function addMember() {
      const nom = $("nomInput").value.trim();
      if (!nom) { alert("Entrez le nom du membre."); return; }
      if (ctx.t.membres.some((m) => m.nom.toLowerCase() === nom.toLowerCase())
          && !confirm(`« ${nom} » existe déjà. L'ajouter quand même ?`)) return;
      ctx.t.membres.push(T.newMember(nom, $("telInput").value.trim()));
      $("nomInput").value = ""; $("telInput").value = "";
      $("nomInput").focus();
      ctx.commit();
      ctx.setStatus(`« ${nom} » ajouté.`, "ok");
    }
    $("addBtn").onclick = addMember;
    $("nomInput").addEventListener("keydown", (e) => { if (e.key === "Enter") addMember(); });
    $("telInput").addEventListener("keydown", (e) => { if (e.key === "Enter") addMember(); });

    // --- Actions membres ---
    $("btnPointage").onclick = () => ui.dlgPointage(ctx);
    $("btnEdit").onclick = () => ui.dlgEditMember(ctx);
    $("btnUp").onclick = () => move(-1);
    $("btnDown").onclick = () => move(1);
    $("btnDel").onclick = () => {
      const m = ui.selected(ctx); if (!m) return;
      if (!confirm(`Retirer « ${m.nom} » ?`)) return;
      ctx.t.membres = ctx.t.membres.filter((x) => x.id !== m.id);
      ctx.selectedId = null;
      ctx.commit(); ctx.setStatus(`« ${m.nom} » retiré.`, "danger");
    };
    function move(dir) {
      const i = ctx.t.membres.findIndex((m) => m.id === ctx.selectedId);
      if (i < 0) { ctx.setStatus("Sélectionnez un membre.", "danger"); return; }
      const j = i + dir;
      if (j < 0 || j >= ctx.t.membres.length) return;
      const ms = ctx.t.membres;
      [ms[i], ms[j]] = [ms[j], ms[i]];
      ctx.commit();
    }

    // --- Actions globales ---
    $("btnHistory").onclick = () => ui.dlgHistory(ctx);
    $("btnCycle").onclick = () => {
      if (!ctx.t.membres.length) return;
      if (!confirm("Démarrer un nouveau cycle ? (la caisse et l'historique sont conservés)")) return;
      ctx.engine.newCycle(ctx.t);
      ctx.commit(); ctx.setStatus(`Cycle ${ctx.t.cycle} démarré.`, "ok");
    };
    $("btnPdf").onclick = () => {
      if (!ctx.t.membres.length) { alert("Ajoutez au moins un membre."); return; }
      T.printDoc(ctx.t, ctx.engine);
    };
    $("btnExport").onclick = () => T.storage.exportFile(ctx.t);
    $("importFile").onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (!confirm("Importer ce fichier remplacera la tontine actuelle. Continuer ?")) { e.target.value = ""; return; }
      T.storage.importFile(file, (state) => {
        ctx.t = state; ctx.selectedId = null; ctx.reloadEngine(); ctx.commit();
        ctx.setStatus("Sauvegarde importée.", "ok");
      });
      e.target.value = "";
    };

    ui.render(ctx);
  });
})(typeof window !== "undefined" ? window : globalThis);
