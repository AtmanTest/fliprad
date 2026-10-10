# FlipRadar — MVP v1 (site statique, sans serveur)

Aide à l'achat-revente : Top 10 Achats et Top 10 Ventes par niche (LEGO neuf scellé, outils électroportatifs, PC portables pro), avec marge nette, score /100, risques et message de négociation. Spécification : [PROMPT.md](PROMPT.md).

**Aucun serveur** : tout tourne dans le navigateur (`docs/index.html` + `docs/engine.js`), les données sont dans le `localStorage`. À déployer tel quel sur n'importe quel hébergeur statique (dossier `docs/`).

## État : réel / simulé
| Élément | État |
|---|---|
| Moteur (normalisation, valorisation, marge, risques, score), UI, suivi, import manuel, calculateur | Réel |
| Capture des badges « Achat en cours » / « Vendu » | Réel (via import) |
| Données | **Aucune donnée fictive** : la base démarre vide, seules les annonces importées existent |
| Source Leboncoin automatique | Non branchée (pas d'API publique, scraping contraire aux CGU et protégé par anti-bot : non contourné) |

Pour de vraies données : onglet **Import** (`titre;prix;statut;url;lieu;état;avis;description`).

## Logique
Revente = médiane des ventes observées du modèle (120 j, normalisées par état), sinon estimé (confiance basse). Marge nette = revente − frais − emballage − remise en état − (prix + frais acheteur + livraison). Score = 100 × facteur marge × (base + poids vitesse × vitesse + poids confiance × confiance) × (1 − risque). Ajouter un modèle : tableau `PRODUCTS` dans `docs/engine.js`.

## Limites
Données propres à chaque navigateur (pas de synchro), pas de distance/géoloc, pas d'alertes (il faudrait un back-end), pas de tests automatisés sur la version JS.
