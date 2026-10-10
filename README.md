# FlipRadar — MVP v1

Aide à l'achat-revente (flipping) : Top 10 Achats et Top 10 Ventes par niche, avec marge nette, score /100, risques et message de négociation.
Niches actives : **LEGO neuf scellé**, **outils électroportatifs de marque**, **PC portables pro**. Spécification : [PROMPT.md](PROMPT.md).

## Lancer (aucune dépendance, Python 3.10+)

    python3 app.py            # http://localhost:8000
    python3 app.py --reseed   # repart de zéro avec de nouvelles données de démo
    python3 -m unittest discover tests

## État du MVP — ce qui est réel / simulé

| Élément | État |
|---|---|
| Moteur (normalisation, valorisation, marge, risques, score), UI, suivi des deals, import manuel, calculateur | **Réel** |
| Capture des badges « Achat en cours » / « Vendu » (statut + date, table `snapshots`) | **Réel** (via import ou adaptateur) |
| Annonces affichées au démarrage | **DÉMO synthétique** (`demo=1`, bandeau dans l'UI). Aucun prix réel de marché. |
| Bouton « Scanner » | Simule des nouvelles annonces et des changements de statut |
| Source Leboncoin automatique | **Non branchée** (voir ci-dessous) |
| Sources externes de prix vendus (eBay…), analyse d'images, alertes, recalibrage | Jalons 2–3 |

## Sources
Leboncoin n'a pas d'API publique ; son scraping est contraire à ses CGU et protégé par un anti-bot. Ce projet **ne le contourne pas**.
Pour de vraies données : (1) **Import** de l'UI (collez des lignes `titre;prix;statut;url;lieu;état;avis`), (2) un prestataire de données autorisé branché dans `sources.py` (`LeboncoinAdapter`, qui renvoie des dicts au format de `upsert`).
Aucune action automatique sur les plateformes : l'app conseille, vous agissez.

## Logique
- **Revente** = médiane des ventes observées du modèle (120 j, normalisées par état) ; sinon estimé (annonces actives −10 % ou 60 % du prix neuf) avec confiance basse.
- **Marge nette** = revente − frais − emballage − remise en état − (prix + frais acheteur + livraison/déplacement).
- **Score** = 100 × facteur marge × (base + poids vitesse × vitesse + poids confiance × confiance) × (1 − risque). Poids réglables.
- **Top Ventes** : rotation observée (ventes/30 j, délai), marge à l'achat bas du marché, prix d'achat max conseillé.
- Ajouter un modèle : `catalog.py` (regex + prix neuf indicatif).

## Limites connues
Pas de géolocalisation/distance, pas de multi-utilisateur, stack Python/SQLite (le prompt visait Next.js/Postgres : migration prévue après validation du moteur).
