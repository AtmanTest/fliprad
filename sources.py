"""Adaptateurs de sources + ingestion.

Chaque source est un module indépendant qui renvoie des dicts d'annonces.
Aucune source ne contourne d'anti-bot : voir README (section Sources).
"""
import csv
import hashlib
import io
import re

import db
import engine

STATUS_MAP = {"": "active", "active": "active", "en ligne": "active", "achat en cours": "achat_en_cours",
              "achat_en_cours": "achat_en_cours", "vendu": "vendu", "sold": "vendu"}


def upsert(conn, d, demo=0):
    """Insère ou met à jour une annonce ; enregistre un snapshot si prix/statut changent."""
    now = db.now()
    text = f"{d['title']} {d.get('description','')}"
    key = d.get("product_key") or engine.match_product(text)
    niche = engine.product_niche(key) if key else None
    cond = d.get("condition") or (engine.detect_condition(text, niche) if niche else "bon")
    status = STATUS_MAP.get(norm_status(d.get("status")), "active")
    row = conn.execute("SELECT * FROM listings WHERE source=? AND ext_id=?", (d["source"], d["ext_id"])).fetchone()
    if row is None:
        first = d.get("first_seen") or now
        sold_at = d.get("sold_at") or (now if status != "active" else None)
        cur = conn.execute(
            "INSERT INTO listings(source,ext_id,url,title,description,price,status,location,condition,product_key,niche,"
            "seller_rating,seller_reviews,delivery_fee,buyer_fee,first_seen,last_seen,sold_at,demo) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (d["source"], d["ext_id"], d.get("url", ""), d["title"], d.get("description", ""), d["price"], status,
             d.get("location", ""), cond, key, niche, d.get("seller_rating"), d.get("seller_reviews"),
             d.get("delivery_fee"), d.get("buyer_fee") or 0.0, first, now, sold_at, demo))
        conn.execute("INSERT INTO snapshots VALUES(?,?,?,?)", (cur.lastrowid, first, d["price"], status))
        return "new"
    changed = row["price"] != d["price"] or row["status"] != status
    sold_at = row["sold_at"] or (now if status != "active" else None)
    conn.execute("UPDATE listings SET price=?, status=?, last_seen=?, sold_at=?, product_key=COALESCE(?,product_key),"
                 " niche=COALESCE(?,niche) WHERE id=?", (d["price"], status, now, sold_at, key, niche, row["id"]))
    if changed:
        conn.execute("INSERT INTO snapshots VALUES(?,?,?,?)", (row["id"], now, d["price"], status))
        return "updated"
    return "unchanged"


def norm_status(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def to_float(x):
    if x is None or str(x).strip() == "":
        return None
    return float(re.sub(r"[^0-9,.\-]", "", str(x)).replace(",", "."))


class ManualImport:
    """Import manuel : lignes CSV `titre;prix;statut;url;lieu;état;avis_vendeur;description`.
    Séparateur ; ou tabulation. Repli légal quand aucune source automatique n'est branchée."""
    name = "import-manuel"

    @staticmethod
    def parse(text):
        text = text.strip()
        if not text:
            return []
        delim = "\t" if "\t" in text.splitlines()[0] else ";"
        out = []
        for i, row in enumerate(csv.reader(io.StringIO(text), delimiter=delim)):
            if not row or not row[0].strip():
                continue
            if i == 0 and row[0].strip().lower() in ("titre", "title"):
                continue
            row += [""] * (8 - len(row))
            title, price, status, url, loc, cond, reviews, desc = [c.strip() for c in row[:8]]
            p = to_float(price)
            if p is None:
                continue
            ext = url or hashlib.sha1(f"{title}|{p}|{loc}".encode()).hexdigest()[:16]
            out.append({"source": "import-manuel", "ext_id": ext, "url": url, "title": title, "price": p,
                        "status": status, "location": loc, "condition": cond or None,
                        "seller_reviews": int(reviews) if reviews.isdigit() else None, "description": desc})
        return out


class LeboncoinAdapter:
    """Emplacement réservé. Leboncoin n'a pas d'API publique et son scraping est contraire à ses CGU
    (protégé par DataDome). Brancher ici un prestataire de données autorisé ou un flux d'alertes,
    en renvoyant des dicts au format de `upsert`. Ne pas contourner d'anti-bot."""
    name = "leboncoin"
    enabled = False

    def fetch(self, conn):
        raise NotImplementedError("Source non configurée : utiliser l'import manuel ou un prestataire autorisé.")


def run_scan(conn):
    """Lance les adaptateurs actifs. Renvoie un rapport par source."""
    import seed
    report = []
    ev = seed.DemoAdapter().fetch(conn)
    counts = {"new": 0, "updated": 0, "unchanged": 0}
    for d in ev:
        counts[upsert(conn, d, demo=1)] += 1
    conn.commit()
    report.append({"source": "demo", "ok": True, **counts})
    report.append({"source": "leboncoin", "ok": False, "error": "Non configurée (voir README › Sources)"})
    return report
