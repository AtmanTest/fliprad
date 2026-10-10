"""Catalogue des niches et des modèles reconnus.

`demo_price` / `demo_demand` ne servent QU'À générer les données de démonstration
(seed.py). Le moteur d'analyse ne les utilise jamais : il se base sur les
observations en base (badges « Vendu » / « Achat en cours », annonces actives).
"""

COND_FACTOR = {"neuf": 1.0, "bon": 0.88, "use": 0.75, "degrade": 0.55}
COND_LABEL = {"neuf": "Neuf / scellé", "bon": "Bon état", "use": "Usagé", "degrade": "Dégradé / incomplet"}

NICHES = [
    # slug, nom, catégorie, activée, sûreté (a priori), fee%, emballage, remise en état, livraison par défaut, note
    ("lego", "LEGO neuf scellé", "Loisirs", 1, 90, 0.0, 4.0, 0.0, 5.5,
     "Référence unique, aucun test, valeur stable. Risque : fausse boîte rescellée."),
    ("outils", "Outils électroportatifs de marque", "Matériel pro", 1, 78, 0.0, 3.0, 0.0, 7.0,
     "Demande constante, modèles robustes. Risque : usure moteur, batteries non fournies."),
    ("pc-pro", "PC portables pro reconditionnables", "Électronique", 1, 66, 0.0, 5.0, 12.0, 8.0,
     "Modèles très documentés. Risques : batterie, verrou BIOS/MDM, écran."),
    ("smartphones", "Smartphones", "Électronique", 0, 38, 0.0, 3.0, 10.0, 6.0,
     "Verrous iCloud/SIM, batterie, contrefaçons : retours fréquents."),
    ("mode", "Vêtements & chaussures", "Mode", 0, 35, 0.0, 2.0, 3.0, 5.0,
     "Tailles, contrefaçon, retours élevés."),
    ("maison", "Meubles & électroménager", "Maison & Jardin", 0, 40, 0.0, 0.0, 0.0, 0.0,
     "Encombrement, pannes cachées, transport."),
    ("famille", "Famille & puériculture", "Famille", 0, 45, 0.0, 3.0, 3.0, 6.0,
     "Normes de sécurité, usure, demande saisonnière."),
    ("emploi", "Emploi", "Emploi", 0, 0, 0.0, 0.0, 0.0, 0.0,
     "Pas de flip possible : catégorie exclue du scoring."),
    ("autres", "Autres", "Autres", 0, 30, 0.0, 3.0, 0.0, 6.0, "Trop hétérogène pour un scoring fiable."),
]

# key, niche, nom, regex (sur texte normalisé), prix neuf indicatif, noms pour titres démo, prix marché démo, demande démo
PRODUCTS = [
    # --- LEGO ---
    ("lego-75192", "lego", "LEGO Star Wars 75192 Faucon Millenium UCS", [r"\b75192\b"], 849.99,
     ["Lego Star Wars 75192 Faucon Millenium"], 760, 0.55),
    ("lego-75313", "lego", "LEGO Star Wars 75313 AT-AT UCS", [r"\b75313\b"], 849.99,
     ["Lego 75313 AT-AT Star Wars"], 720, 0.5),
    ("lego-10276", "lego", "LEGO Icons 10276 Colisée", [r"\b10276\b"], 549.99,
     ["Lego Icons 10276 Colisée"], 470, 0.5),
    ("lego-21322", "lego", "LEGO Ideas 21322 Barracuda Bay", [r"\b21322\b"], 199.99,
     ["Lego Ideas 21322 Baie des pirates"], 165, 0.7),
    ("lego-10281", "lego", "LEGO Icons 10281 Bonsaï", [r"\b10281\b"], 49.99,
     ["Lego 10281 Bonsaï"], 42, 0.85),
    ("lego-42115", "lego", "LEGO Technic 42115 Lamborghini Sián", [r"\b42115\b"], 449.99,
     ["Lego Technic 42115 Lamborghini Sian"], 380, 0.6),
    ("lego-10305", "lego", "LEGO Icons 10305 Château des Chevaliers du Lion", [r"\b10305\b"], 399.99,
     ["Lego 10305 Château des chevaliers du lion"], 350, 0.65),
    ("lego-76240", "lego", "LEGO Batman 76240 Batmobile Tumbler", [r"\b76240\b"], 229.99,
     ["Lego DC 76240 Batmobile Tumbler"], 190, 0.6),
    # --- Outils ---
    ("makita-dhp484", "outils", "Makita DHP484 perceuse-visseuse 18V", [r"\bdhp\s?484\b"], 140,
     ["Makita DHP484 perceuse à percussion 18V", "Perceuse visseuse Makita DHP484"], 75, 0.8),
    ("makita-dtw1002", "outils", "Makita DTW1002 boulonneuse 1/2\" 18V", [r"\bdtw\s?1002\b"], 290,
     ["Makita DTW1002 clé à chocs 18V", "Boulonneuse Makita DTW1002"], 150, 0.55),
    ("dewalt-dcd796", "outils", "DeWalt DCD796 perceuse-visseuse 18V", [r"\bdcd\s?796\b"], 150,
     ["DeWalt DCD796 perceuse visseuse 18V brushless", "Perceuse DeWalt DCD796"], 85, 0.75),
    ("dewalt-dcf887", "outils", "DeWalt DCF887 visseuse à chocs 18V", [r"\bdcf\s?887\b"], 140,
     ["DeWalt DCF887 visseuse à chocs", "Visseuse à chocs DeWalt DCF887 18V"], 80, 0.7),
    ("milwaukee-fpd3", "outils", "Milwaukee M18 FPD3 perceuse à percussion", [r"\bm18\s?fpd\s?[23]?\b"], 200,
     ["Milwaukee M18 FPD3 perceuse à percussion", "Perceuse Milwaukee M18 FPD2"], 110, 0.7),
    ("milwaukee-fid3", "outils", "Milwaukee M18 FID3 visseuse à chocs", [r"\bm18\s?fid\s?[23]?\b"], 190,
     ["Milwaukee M18 FID3 visseuse à chocs", "Visseuse à chocs Milwaukee M18 FID2"], 105, 0.65),
    ("bosch-gsr1855", "outils", "Bosch Professional GSR 18V-55", [r"\bgsr\s?18\s?v?\s?-?\s?55\b"], 150,
     ["Bosch Professional GSR 18V-55 perceuse", "Perceuse visseuse Bosch GSR 18V-55"], 75, 0.6),
    ("bosch-gbh1826", "outils", "Bosch Professional GBH 18V-26 perforateur", [r"\bgbh\s?18\s?v?\s?-?\s?26\b"], 260,
     ["Bosch GBH 18V-26 perforateur SDS+", "Perforateur Bosch Professional GBH 18V-26"], 120, 0.6),
    # --- PC pro ---
    ("tp-x395", "pc-pro", "Lenovo ThinkPad X395", [r"\bx\s?395\b"], None,
     ["PC portable Lenovo ThinkPad X395", "ThinkPad X395 Ryzen"], 150, 0.6),
    ("tp-t480", "pc-pro", "Lenovo ThinkPad T480", [r"\bt\s?480\b(?!\s?s)"], None,
     ["PC portable Lenovo ThinkPad T480", "ThinkPad T480 i5 8Go"], 165, 0.8),
    ("tp-t14g2", "pc-pro", "Lenovo ThinkPad T14 Gen 2", [r"\bt14\b.{0,12}\bgen\s?2\b", r"\bt14\s?g2\b"], None,
     ["Lenovo ThinkPad T14 Gen 2 i5", "PC portable ThinkPad T14 Gen 2"], 380, 0.65),
    ("tp-x1c7", "pc-pro", "Lenovo ThinkPad X1 Carbon Gen 7", [r"\bx1\s?carbon\b.{0,12}\b(gen\s?7|7th|7eme)\b", r"\bx1\s?carbon\s?g7\b"], None,
     ["Lenovo ThinkPad X1 Carbon Gen 7", "ThinkPad X1 Carbon 7th gen i7"], 290, 0.55),
    ("dell-5420", "pc-pro", "Dell Latitude 5420", [r"\blatitude\s?5420\b"], None,
     ["PC portable Dell Latitude 5420", "Dell Latitude 5420 i5 11e gen"], 270, 0.65),
    ("dell-7420", "pc-pro", "Dell Latitude 7420", [r"\blatitude\s?7420\b"], None,
     ["Dell Latitude 7420 i7", "PC portable Dell Latitude 7420"], 330, 0.5),
    ("hp-840g7", "pc-pro", "HP EliteBook 840 G7", [r"\belitebook\s?840\s?g\s?7\b"], None,
     ["HP EliteBook 840 G7 i5", "PC portable HP EliteBook 840 G7"], 310, 0.6),
]
