# 🤝 Tontino

Gestion de tontine

## ✨ Fonctionnalités

- 🍽️ **Deux cartes vedettes en haut** : **« BOUFFE MAINTENANT »** et **« PROCHAIN À BOUFFER »** —
  on sait toujours qui reçoit la cagnotte cette séance et qui l'aura à la suivante
- 👥 **Membres** — ajouter, modifier, supprimer, et **réordonner** (↑ ↓) pour fixer l'ordre de passage
- 💰 **Cotisation paramétrable** (ex. 30 000 F) → cagnotte = cotisation × nombre de membres
- 📝 **Pointage de séance** par membre (double-clic) : présence/absence + cotisation payée + pénalités
- 🏦 **Caisse d'épargne** alimentée automatiquement par les **pénalités** (non distribuée) :
  - Absence · Retard physique · Retard cotisation · Échec cotisation (montants paramétrables)
- 🍽️ **« A bouffé »** — qui a déjà reçu la cagnotte **et à quelle date**
- 🎁 **Prochain bénéficiaire** désigné automatiquement (le 1ᵉʳ qui n'a pas encore bouffé)
- 🏁 **Clôturer le tour** — remet la cagnotte au bénéficiaire, ajoute les pénalités à la caisse,
  enregistre la date, passe au tour suivant
- 📜 **Historique détaillé** des tours passés : qui a bouffé, quand, et le **détail des pénalités**
  (qui a été pénalisé, pour quel motif, quel montant)
- 🔄 **Nouveau cycle** quand tout le monde a bouffé (caisse + historique conservés)
- 📊 **Récapitulatif en direct** — tour, cagnotte, cotisations collectées, caisse, prochain bénéficiaire
- 📄 **Export PDF style facture** (sobre) : statut de chaque membre (a bouffé / prochain / en attente),
  caisse, historique et détail des pénalités
- 💾 **Sauvegarde automatique** dans `tontine.json` (aucune connexion requise)

## 🚀 Installation

> Prérequis : **Python 3.10+** (Tkinter inclus avec Python sous Windows).

```bash
pip install -r requirements.txt
python tontino.py
```

© 2026 **Dipeua Berthold**
