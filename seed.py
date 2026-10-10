"""Données de DÉMONSTRATION (synthétiques, marquées demo=1) + adaptateur de démo.

Rien ici ne représente de vraies annonces. Le but : pouvoir tester le moteur et l'UI
tant qu'aucune source réelle n'est branchée.
"""
import random

import db
from catalog import COND_FACTOR, NICHES, PRODUCTS

CITIES = ["Champs-sur-Marne 77420", "Paris 75011", "Lyon 69003", "Lille 59000", "Nantes 44000", "Bordeaux 33000",
          "Marseille 13006", "Toulouse 31000", "Créteil 94000", "Versailles 78000", "Rennes 35000", "Montreuil 93100"]
SELLERS = ["La Chouineuse", "Marc_77", "bricoleur33", "Sophie L", "TechOccaz", "papa-lego", "Nico", "AtelierJo"]


def _title(rng, p, cond):
    base = rng.choice(p[5])
    niche = p[1]
    if niche == "lego":
        tag = {"neuf": rng.choice(["neuf scellé", "neuf sous blister", "jamais ouvert"]),
               "degrade": rng.choice(["sans notice", "monté, incomplet"])}[cond]
    elif niche == "outils":
        tag = {"neuf": "neuf", "bon": rng.choice(["très bon état", "machine seule"]), "use": "usage chantier"}[cond]
    else:
        tag = {"bon": rng.choice(["très bon état", "SSD 256Go"]), "use": rng.choice(["rayures légères", "état correct"])}[cond]
    return f"{base} - {tag}"


def _cond(rng, niche):
    r = rng.random()
    if niche == "lego":
        return "neuf" if r < 0.88 else "degrade"
    if niche == "outils":
        return "neuf" if r < 0.25 else "bon" if r < 0.75 else "use"
    return "bon" if r < 0.65 else "use"


def _listing(rng, p, now, age_days, forced_ratio=None, tag="s"):
    cond = _cond(rng, p[1])
    M = p[6] * COND_FACTOR[cond] / (COND_FACTOR["neuf"] if p[1] == "lego" else COND_FACTOR["bon"]) \
        if p[1] != "lego" else p[6] * COND_FACTOR[cond]
    ratio = forced_ratio if forced_ratio else min(1.3, max(0.78, rng.gauss(1.0, 0.09)))
    price = round(M * ratio / 5) * 5 or 5
    desc = ""
    reviews = rng.choice([0, 3, 12, 40, 90, 154, 200]) if ratio > 0.5 else 0
    if forced_ratio and forced_ratio < 0.5:
        desc = "Contactez-moi sur WhatsApp, paiement par virement ou PayPal ami famille."
        reviews = 0
    elif rng.random() < 0.05:
        desc = "Vendu pour pièces, ne s'allume pas."
        price = round(price * 0.35)
    ext = f"demo-{tag}-{rng.getrandbits(40):x}"
    return ratio, {
        "source": "demo", "ext_id": ext, "url": f"https://example.invalid/demo/{ext}", "title": _title(rng, p, cond),
        "description": desc, "price": price, "location": rng.choice(CITIES), "condition": cond, "product_key": p[0],
        "seller_rating": round(rng.uniform(3.6, 5.0), 1), "seller_reviews": reviews,
        "delivery_fee": rng.choice([5.49, 6.49, 7.99]), "buyer_fee": 1.99,
        "first_seen": now - int(age_days * 86400)}


def seed(conn, rng_seed=42):
    rng = random.Random(rng_seed)
    now = db.now()
    for n in NICHES:
        conn.execute("INSERT OR IGNORE INTO niches VALUES(?,?,?,?,?,?,?,?,?,?)", n)
    for p in PRODUCTS:
        conn.execute("INSERT OR IGNORE INTO products VALUES(?,?,?,?)", (p[0], p[1], p[2], p[4]))
    import sources
    for p in PRODUCTS:
        demand = p[7]
        mean_days = 40 * (1 - 0.6 * demand)
        # historique sur 100 jours
        for i in range(rng.randint(26, 40)):
            age = rng.uniform(0, 100)
            ratio, d = _listing(rng, p, now, age, tag="h")
            if d["price"] < 0.5 * p[6]:
                continue
            days = rng.expovariate(1 / (mean_days * ratio ** 4))
            if age > days:
                recent = (age - days) < 2
                d["status"] = "achat_en_cours" if recent and rng.random() < 0.6 else "vendu"
                d["sold_at"] = now - int((age - days) * 86400)
            sources.upsert(conn, d, demo=1)
        # annonces fraîches encore en ligne, dont quelques bonnes affaires
        for j in range(rng.randint(6, 10)):
            fr = rng.choice([0.58, 0.66, 0.72, 0.78]) if j < 2 else (0.4 if j == 2 and rng.random() < .35 else None)
            _, d = _listing(rng, p, now, rng.uniform(0, 12), forced_ratio=fr, tag="a")
            d["status"] = "active"
            sources.upsert(conn, d, demo=1)
    conn.commit()


class DemoAdapter:
    """Simule un scan : nouvelles annonces + passage de certaines annonces en « Achat en cours » / « Vendu »."""
    name = "demo"

    def fetch(self, conn):
        rng = random.Random(db.now())
        now = db.now()
        out = []
        for _ in range(rng.randint(3, 6)):
            p = rng.choice(PRODUCTS)
            fr = rng.choice([0.62, 0.7, 0.75, None])
            _, d = _listing(rng, p, now, 0, forced_ratio=fr, tag="n")
            d["status"] = "active"
            out.append(d)
        rows = conn.execute("SELECT * FROM listings WHERE source='demo' AND status!='vendu' ORDER BY RANDOM() LIMIT 40").fetchall()
        for r in rows:
            if r["status"] == "active" and rng.random() < 0.15:
                new = "achat_en_cours"
            elif r["status"] == "achat_en_cours" and rng.random() < 0.7:
                new = "vendu"
            else:
                continue
            out.append({"source": "demo", "ext_id": r["ext_id"], "title": r["title"], "price": r["price"], "status": new})
        return out
