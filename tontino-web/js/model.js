/* model.js — état de la tontine et helpers neutres (sans logique de type). */
(function (root) {
  const T = (root.Tontino = root.Tontino || {});

  T.PENALITES_DEFAUT = {
    absence: 1000, retard_physique: 500, retard_cotisation: 1000, echec_cotisation: 5000,
  };
  T.PENALITES_LABELS = {
    absence: "Absence", retard_physique: "Retard physique",
    retard_cotisation: "Retard cotisation", echec_cotisation: "Échec cotisation",
  };
  T.TYPES = {
    rotative: "Rotative (tour de rôle)",
    encheres: "À enchères (mises)",
    epargne: "Épargne (accumulation)",
  };
  T.ORDRES = { fixe: "Ordre fixe", tirage: "Tirage au sort" };

  T.seanceVierge = function () {
    return {
      presence: null, cotise: false, retard_physique: false,
      retard_cotisation: false, echec_cotisation: false,
    };
  };

  T.newMember = function (nom, tel) {
    return {
      id: T.uid(), nom: nom, tel: tel || "", recu: false, date_recu: null,
      epargne: 0, seance: T.seanceVierge(),
    };
  };

  T.defaultState = function () {
    return {
      nom: "Ma tontine", type: "rotative", ordre: "fixe", cotisation: 30000,
      penalites: Object.assign({}, T.PENALITES_DEFAUT),
      tour: 1, cycle: 1, caisse: 0, fonds: 0, membres: [], historique: [],
    };
  };

  /* --- Helpers neutres --- */
  T.restants = (t) => t.membres.filter((m) => !m.recu);
  T.cagnotte = (t) => t.cotisation * t.membres.length;

  T.penaliteMembre = function (t, m) {
    const s = m.seance, p = t.penalites;
    let x = 0;
    if (s.presence === "absent") x += p.absence;
    if (s.retard_physique) x += p.retard_physique;
    if (s.retard_cotisation) x += p.retard_cotisation;
    if (s.echec_cotisation) x += p.echec_cotisation;
    return x;
  };

  T.penalitesSeance = (t) => t.membres.reduce((s, m) => s + T.penaliteMembre(t, m), 0);

  T.detailsPenalites = function (t) {
    const L = T.PENALITES_LABELS, out = [];
    t.membres.forEach((m) => {
      const s = m.seance, motifs = [];
      if (s.presence === "absent") motifs.push(L.absence);
      if (s.retard_physique) motifs.push(L.retard_physique);
      if (s.retard_cotisation) motifs.push(L.retard_cotisation);
      if (s.echec_cotisation) motifs.push(L.echec_cotisation);
      const montant = T.penaliteMembre(t, m);
      if (montant > 0) out.push({ nom: m.nom, motifs, montant });
    });
    return out;
  };

  T.resetSeances = function (t) {
    t.membres.forEach((m) => (m.seance = T.seanceVierge()));
  };

  /* Normalise un état chargé (compat / valeurs manquantes). */
  T.normalize = function (d) {
    const def = T.defaultState();
    if (!d || typeof d !== "object") return def;
    const t = Object.assign(def, {
      nom: String(d.nom || "Ma tontine"),
      type: ["rotative", "encheres", "epargne"].includes(d.type) ? d.type : "rotative",
      ordre: d.ordre === "tirage" ? "tirage" : "fixe",
      cotisation: T.parseInt(d.cotisation) || 30000,
      tour: Math.max(1, parseInt(d.tour, 10) || 1),
      cycle: Math.max(1, parseInt(d.cycle, 10) || 1),
      caisse: parseInt(d.caisse, 10) || 0,
      fonds: parseInt(d.fonds, 10) || 0,
    });
    t.penalites = Object.assign({}, T.PENALITES_DEFAUT, d.penalites || {});
    t.membres = (Array.isArray(d.membres) ? d.membres : []).filter((m) => m && m.nom).map((m) => ({
      id: m.id || T.uid(), nom: String(m.nom), tel: String(m.tel || ""),
      recu: !!m.recu, date_recu: m.date_recu || null, epargne: parseInt(m.epargne, 10) || 0,
      seance: Object.assign(T.seanceVierge(), m.seance || {}),
    }));
    t.historique = Array.isArray(d.historique) ? d.historique : [];
    return t;
  };
})(typeof window !== "undefined" ? window : globalThis);
