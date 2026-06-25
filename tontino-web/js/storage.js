/* storage.js — persistance locale (localStorage) + export/import d'une sauvegarde. */
(function (root) {
  const T = (root.Tontino = root.Tontino || {});
  const KEY = "tontino_web_v1";

  T.storage = {
    load() {
      try {
        const raw = localStorage.getItem(KEY);
        if (!raw) return T.defaultState();
        return T.normalize(JSON.parse(raw));
      } catch (e) {
        return T.defaultState();
      }
    },
    save(t) {
      try {
        localStorage.setItem(KEY, JSON.stringify(t));
      } catch (e) {
        alert("Sauvegarde impossible : " + e.message);
      }
    },
    /* Télécharge un fichier de sauvegarde JSON. */
    exportFile(t) {
      const blob = new Blob([JSON.stringify(t, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const safe = (t.nom || "tontine").replace(/[^\w\-]+/g, "_");
      a.href = url;
      a.download = `${safe}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },
    /* Lit un fichier choisi par l'utilisateur, renvoie l'état via callback. */
    importFile(file, cb) {
      const r = new FileReader();
      r.onload = () => {
        try {
          cb(T.normalize(JSON.parse(r.result)));
        } catch (e) {
          alert("Fichier illisible : " + e.message);
        }
      };
      r.readAsText(file);
    },
  };
})(typeof window !== "undefined" ? window : globalThis);
