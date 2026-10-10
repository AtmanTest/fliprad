# PROMPT DE DÉVELOPPEMENT — « FlipRadar » (nom provisoire)

## 1. Rôle et objectif

Tu es un lead dev full-stack + data engineer. Construis une **application web d'aide à l'achat-revente** (flipping) sur le marché de l'occasion français. L'app scanne en continu les annonces, les analyse, et affiche pour **chaque niche/catégorie un Top 10 des meilleures opportunités d'achat** et un **Top 10 des produits qui se revendent le mieux** (rapidité + marge).

But final : permettre à l'utilisateur de trouver en quelques secondes « quoi acheter, à quel prix max, pour le revendre où, à quel prix, en combien de temps, avec quelle marge nette ».

## 2. Niches / catégories (arbre de navigation)

Reprendre l'arbre de catégories type Leboncoin, avec sous-niches affinables :

- Matériel pro
- Emploi (service uniquement : pas de flip, à exclure du scoring ou à traiter en « veille »)
- Mode
- Maison & Jardin
- Famille
- Électronique
- Loisirs
- Autres

Chaque catégorie doit être extensible en sous-niches (ex. Électronique → consoles, smartphones, photo, audio, PC portables ; Loisirs → vélo, instruments, jeux de société, collection). Les niches sont **configurables en base** (pas codées en dur) et l'utilisateur peut créer des niches personnalisées (mots-clés + filtres + zone géographique).

### Niches prioritaires du MVP (critère : le plus safe, le moins de retours)

Un **« score de sûreté » par niche** (0–100) est calculé et affiché : produit standardisé (référence modèle exacte), pas de taille/ajustement, peu de panne cachée, testable en 2 minutes, expédiable facilement, pas de verrouillage logiciel, faible risque de contrefaçon, demande stable, prix peu volatil.

Niches retenues pour le Jalon 1 :
1. **LEGO neuf scellé / sets complets** — référence numérotée unique, aucun test nécessaire, aucun retour d'« état », valeur stable voire croissante sur les sets retirés de la vente.
2. **Outils électroportatifs de marque** (Makita, Milwaukee, DeWalt, Bosch Professional, Hilti — en « machine seule » ou packs) — demande constante côté pros/bricoleurs, références claires, robustes, testables rapidement.
3. **PC portables professionnels reconditionnables** (Lenovo ThinkPad, Dell Latitude, HP EliteBook — cf. annonce ThinkPad X395 vue sur Leboncoin) — modèles très documentés, prix de revente bien repérables, forte demande reconditionné ; risques à scorer : batterie, verrou BIOS/MDM, écran.

Niches **déprioritisées/à risque** (affichées avec avertissement, désactivées par défaut) : smartphones (iCloud, batterie), vêtements/chaussures (tailles, contrefaçon), meubles (encombrement), électroménager (pannes), produits fragiles ou lourds, cartes graphiques d'occasion (minage, pannes).

Les 3 niches ci-dessus sont des hypothèses à **valider avec des données réelles** au Jalon 1 (mesurer taux de « Vendu », marge nette, dispersion des prix) ; l'app doit pouvoir reclasser les niches par score de sûreté mesuré.

## 3. Fonctionnalités cœur

### 3.1 Dashboard par niche
Pour chaque niche, deux classements Top 10, rafraîchis automatiquement :

1. **Top 10 Achats** : annonces actuellement en ligne avec le meilleur score d'opportunité.
2. **Top 10 Ventes** : modèles/produits de la niche qui se revendent le mieux (rotation rapide + marge nette élevée + volume), avec prix d'achat cible conseillé.

Chaque ligne affiche : photo, titre, prix demandé, **prix de revente estimé** (fourchette), **marge nette estimée** (€ et %), **délai de vente estimé**, **score d'opportunité /100**, **niveau de confiance**, distance, ancienneté de l'annonce, lien source, boutons « Ajouter au suivi » / « Ignorer » / « Alerter ».

### 3.2 Moteur d'analyse « intelligent »
Pipeline par annonce :

1. **Normalisation** : extraction marque / modèle / capacité / état / accessoires fournis depuis titre + description + photos (LLM avec sortie JSON stricte + règles + dictionnaires). Dédoublonnage (même vendeur, annonces recopiées, reposts).
2. **Estimation de la valeur de revente** : prix médian/P25/P75 des produits équivalents à partir de :
   - annonces actives comparables (même modèle, même état),
   - historique des annonces **disparues** (proxy de vente — voir §4),
   - sources externes de prix **vendus** (eBay ventes terminées, Vinted, Back Market / reconditionné, prix neuf constructeur comme plafond).
3. **Coût réel** : frais de plateforme de revente, commission, frais de port, emballage, réparation/remise en état estimée, coût de déplacement. **Marge nette = revente − achat − tous les coûts.**
4. **Score d'opportunité** (0–100), formule transparente et pondérable par l'utilisateur :
   `marge nette` × `probabilité de vente` × `vitesse de rotation` × `confiance des données` − `risque`.
5. **Détection de risques** : arnaque (prix trop bas, paiement hors plateforme, vendeur neuf, photos volées via recherche d'image inversée), contrefaçon, produit volé/bloqué (iCloud, SIM-lock), état douteux, annonce en « remise en main propre uniquement » sur un produit fragile à expédier.
6. **Analyse d'images** (modèle vision) : état réel, rayures, manque d'accessoires, cohérence avec la description.
7. **Explication** : pour chaque score, afficher le « pourquoi » en 3 lignes (comparables utilisés, hypothèses, risques).

### 3.3 Scans et alertes
- Scans planifiés par niche (fréquence configurable : 5 min à 24 h) + « scan manuel ».
- **Alertes temps réel** (email, Telegram/Discord/push) quand une annonce dépasse un seuil de score/marge, avec prix max de négociation et message pré-rédigé au vendeur (à envoyer **manuellement** par l'utilisateur).
- Détection de **baisses de prix** et d'annonces vieillissantes (levier de négociation).

### 3.4 Suivi du business
- Pipeline : *Repéré → Contacté → Acheté → En vente → Vendu* avec prix réels.
- Tableau de bord ROI : marge réelle vs estimée, capital immobilisé, temps moyen de revente, meilleures niches. Le moteur **apprend** de ces données réelles pour recalibrer ses estimations.
- Export CSV.

### 3.5 Outils annexes
- **Calculateur** achat/revente manuel (coller une URL ou saisir un modèle).
- **Graphiques de tendance** par modèle (prix médian, volume d'annonces, délai de disparition) sur 30/90/180 jours.
- **Alerte saisonnalité** (ex. vélos au printemps, matériel de ski à l'automne).
- **Cartographie** : zones géographiques avec les meilleurs écarts de prix (acheter où c'est peu cher, revendre où c'est cher).

## 4. Point de vigilance essentiel : « ce qui se vend »

Les plateformes n'affichent pas toutes les ventes conclues. Mais Leboncoin affiche, sur les annonces avec livraison/paiement sécurisé, des **badges de statut** (« Achat en cours », « Vendu »). Ce sont les **seules ventes observées** : à capturer à chaque scan dans `listing_snapshots` (statut + horodatage), et à traiter comme vérité terrain (`confiance = haute`).

Les annonces sans badge (remise en main propre) restent invisibles : le « Top 10 Ventes » doit donc combiner les badges et des **proxys explicites** :
- **badge « Achat en cours » / « Vendu »** + délai entre mise en ligne et passage au statut (= vitesse de vente réelle, métrique n°1) ;
- taux de conversion par modèle = annonces passées « Vendu » / annonces totales vues (attention au biais : n'inclut que les annonces avec paiement sécurisé, à signaler dans l'UI) ;
- annonce disparue rapidement sans baisse de prix = probablement vendue (indice de rotation) ;
- ratio annonces disparues / annonces actives par modèle ;
- prix vendus publics (eBay, etc.) ;
- baisses de prix successives avant disparition.

Chaque métrique doit être étiquetée *« observé »* ou *« estimé »* avec un niveau de confiance. **Ne jamais présenter une estimation comme une vente confirmée.**

## 5. Sources de données — contraintes légales et techniques

- Concevoir une **architecture d'adaptateurs de sources** (`SourceAdapter`) : Leboncoin, Vinted, eBay, Facebook Marketplace, Back Market, etc. Chaque source est un module indépendant et désactivable.
- Pour chaque source, **privilégier dans l'ordre** : API officielle/partenaire → fournisseur de données tiers (ex. Apify, Bright Data, ou équivalent) → recherches sauvegardées/alertes email de la plateforme → scraping respectueux.
- Le scraping de Leboncoin est contraire à ses CGU et protégé par des anti-bots (DataDome). **Ne pas contourner de CAPTCHA ni d'anti-bot.** Prévoir : rate limiting strict, respect de robots.txt quand applicable, cache agressif, rotation légitime via prestataire, et une interface « import manuel » (collage d'URL/CSV) comme repli.
- Aucune donnée personnelle de vendeurs stockée au-delà du nécessaire (RGPD) : pseudo/ID anonymisé, pas de téléphone ni d'adresse exacte.
- **Aucune action automatique sur les plateformes** (pas d'envoi de messages, pas d'achat, pas de publication automatiques). L'app conseille, l'humain agit.

## 6. Architecture technique proposée

- **Front** : Next.js (App Router) + TypeScript + Tailwind + shadcn/ui, graphiques Recharts. Responsive, **mobile-first** (usage en déplacement), mode sombre.
- **Back** : API Next.js / ou service Node (Fastify) + **worker de jobs** (BullMQ + Redis) pour scans, analyse, alertes.
- **Base** : PostgreSQL (Drizzle ou Prisma) ; tables : `sources`, `niches`, `listings`, `listing_snapshots` (historique de prix/état pour détecter disparitions), `products` (modèles normalisés), `price_observations`, `scores`, `alerts`, `deals` (suivi business), `users`.
- **IA** : API Claude pour extraction structurée (JSON schema strict), analyse d'image et explications ; cache des résultats par hash d'annonce pour maîtriser les coûts ; règles déterministes avant LLM quand c'est possible.
- **Auth** : e-mail magic link (mono-utilisateur d'abord, multi-utilisateur prévu dans le schéma).
- **Déploiement** : Vercel (front) + Neon/Supabase (Postgres) + Upstash/Redis + worker sur Railway/Fly.io. Variables d'environnement documentées dans `.env.example`.
- **Qualité** : tests unitaires sur le calcul de marge/score, tests d'intégration sur les adaptateurs avec fixtures, logs structurés, page d'état des sources (dernier scan, erreurs).

## 7. UX / écrans

1. **Accueil** : grille des niches avec meilleur deal du jour + KPI (marge potentielle totale, nouvelles opportunités).
2. **Page niche** : onglets *Top 10 Achats* / *Top 10 Ventes* / *Tendances* / *Réglages de la niche*. Filtres : budget max, marge min, distance, état, source.
3. **Fiche opportunité** : galerie, analyse IA, comparables, graphique de prix, risques, calcul de marge détaillé et éditable, message de négociation suggéré.
4. **Suivi** (kanban) et **Statistiques**.
5. **Alertes & Réglages** : seuils, canaux, pondération du score, frais personnalisés, zone géographique.

## 8. Livrables attendus et méthode

Procède **par étapes**, en validant chaque jalon avec moi avant de passer au suivant :

1. **Jalon 0** — Schéma de base de données + maquettes des écrans clés + liste des sources retenues (avec statut légal/technique de chacune). *Stop et validation.*
2. **Jalon 1 (MVP)** — 1 source + les 3 niches prioritaires (LEGO, outils électroportatifs, PC portables pro), capture des badges « Achat en cours » / « Vendu », pipeline normalisation → estimation → score, dashboard Top 10 Achats, fiche opportunité, données de démo si la source n'est pas encore branchée.
3. **Jalon 2** — Historique/snapshots, Top 10 Ventes (proxys de rotation), alertes.
4. **Jalon 3** — Suivi business + recalibrage automatique, sources supplémentaires, analyse d'images.
5. **Jalon 4** — Tendances, saisonnalité, cartographie, polish, déploiement.

À chaque jalon : code propre, README de lancement, ce qui marche / ce qui est simulé, et les décisions à me soumettre.

## 9. Règles de conduite

- Si une information manque (budget, zone géographique, niches prioritaires, capital de départ), **pose-moi la question** plutôt que d'inventer.
- Ne jamais inventer de données de marché : tout chiffre affiché doit être traçable (source + date + nb d'échantillons) ou clairement marqué comme démo.
- Signale-moi toute limite légale/technique rencontrée au lieu de la contourner.
- Commence maintenant par le **Jalon 0**.
