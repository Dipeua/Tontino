/* utils.js — fonctions utilitaires (formatage, parsing). */
(function (root) {
  const T = (root.Tontino = root.Tontino || {});

  T.fmtMoney = function (v) {
    const n = parseInt(v, 10);
    if (isNaN(n)) return "0 FCFA";
    return n.toLocaleString("fr-FR").replace(/ |,/g, " ") + " FCFA";
  };

  T.parseInt = function (x) {
    const d = String(x == null ? "" : x).replace(/\D/g, "");
    return d ? parseInt(d, 10) : 0;
  };

  T.today = function () {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`;
  };

  T.uid = function () {
    return "m" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  };
})(typeof window !== "undefined" ? window : globalThis);
