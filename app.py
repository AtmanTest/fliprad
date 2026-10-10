"""FlipRadar MVP — serveur web sans dépendance (Python 3 + SQLite).
Lancer :  python3 app.py   puis ouvrir http://localhost:8000
"""
import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import db
import engine
import seed
import sources
from catalog import COND_LABEL, PRODUCTS

STATIC = os.path.join(os.path.dirname(__file__), "static")
STAGES = ["repere", "contacte", "achete", "en_vente", "vendu"]


def ensure_db():
    conn = db.connect()
    db.init(conn)
    if conn.execute("SELECT COUNT(*) FROM niches").fetchone()[0] == 0:
        seed.seed(conn)
    return conn


def view_listing(ctx, r, with_comps=False):
    a = engine.analyze(ctx, r)
    out = {k: r[k] for k in ("id", "title", "price", "url", "location", "status", "source", "demo", "niche",
                              "seller_rating", "seller_reviews", "description")}
    out["analysis"] = a
    if with_comps and a.get("analyzable"):
        comps = sorted(ctx.sold.get(r["product_key"], []), key=lambda c: -c["sold_at"])[:10]
        out["comps"] = [{"price": c["price"], "status": c["status"], "days": round(c["days"], 1),
                         "sold_ago": round((ctx.now - c["sold_at"]) / 86400, 1), "condition": COND_LABEL.get(c["condition"])}
                        for c in comps]
    return out


def api_niches(conn, q):
    ctx = engine.Context(conn)
    out = []
    for slug, n in ctx.niches.items():
        item = {k: n[k] for k in ("slug", "name", "category", "enabled", "safety", "note", "fee_pct", "pack_cost", "prep_cost")}
        if n["enabled"]:
            rows = conn.execute("SELECT * FROM listings WHERE niche=? AND status='active' AND ignored=0", (slug,)).fetchall()
            best = None
            n_deals = 0
            for r in rows:
                a = engine.analyze(ctx, r)
                if a.get("analyzable") and not a["blocking"] and a["net"] > 0:
                    n_deals += 1
                    if best is None or a["score"] > best["analysis"]["score"]:
                        best = {"title": r["title"], "id": r["id"], "analysis": a}
            sold30 = sum(ctx.stats(p[0])["sold30"] for p in PRODUCTS if p[1] == slug)
            item.update({"active": len(rows), "deals": n_deals, "sold30": sold30,
                         "safety_measured": engine.niche_safety_measured(ctx, slug),
                         "best": {"id": best["id"], "title": best["title"], "net": best["analysis"]["net"],
                                  "score": best["analysis"]["score"]} if best else None})
        out.append(item)
    out.sort(key=lambda x: (-x["enabled"], -x["safety"]))
    return out


def api_buys(conn, slug, q):
    ctx = engine.Context(conn)
    max_price = float(q.get("max_price", [0])[0] or 0)
    min_margin = float(q.get("min_margin", [0])[0] or 0)
    rows = conn.execute("SELECT * FROM listings WHERE niche=? AND status='active' AND ignored=0", (slug,)).fetchall()
    res = []
    for r in rows:
        if max_price and r["price"] > max_price:
            continue
        v = view_listing(ctx, r)
        a = v["analysis"]
        if not a.get("analyzable") or a["blocking"] or a["net"] < min_margin or a["net"] <= 0:
            continue
        res.append(v)
    res.sort(key=lambda v: -v["analysis"]["score"])
    return {"items": res[:10], "total_candidates": len(res)}


def api_listing(conn, lid):
    ctx = engine.Context(conn)
    r = conn.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
    if not r:
        return None
    return view_listing(ctx, r, with_comps=True)


def api_analyze(conn, body):
    title = body.get("title", "").strip()
    price = sources.to_float(body.get("price"))
    if not title or price is None:
        raise ValueError("titre et prix requis")
    text = f"{title} {body.get('description','')}"
    key = engine.match_product(text)
    niche = engine.product_niche(key) if key else None
    cond = body.get("condition") or (engine.detect_condition(text, niche) if niche else "bon")
    ctx = engine.Context(conn)
    r = {"id": None, "title": title, "description": body.get("description", ""), "price": price, "product_key": key,
         "niche": niche, "condition": cond, "seller_reviews": sources.to_float(body.get("reviews")),
         "seller_rating": None, "delivery_fee": sources.to_float(body.get("delivery_fee")), "buyer_fee": 0.0,
         "first_seen": db.now()}
    return {"title": title, "price": price, "analysis": engine.analyze(ctx, r)}


def api_deals(conn):
    ctx = engine.Context(conn)
    rows = conn.execute("SELECT * FROM deals ORDER BY updated DESC").fetchall()
    stats = {"realised": 0.0, "count_sold": 0, "capital": 0.0}
    out = []
    for d in rows:
        d = dict(d)
        if d["stage"] == "vendu" and d["buy_price"] is not None and d["sell_price"] is not None:
            d["real_net"] = round(d["sell_price"] - d["buy_price"], 2)
            stats["realised"] += d["real_net"]
            stats["count_sold"] += 1
        elif d["stage"] in ("achete", "en_vente") and d["buy_price"]:
            stats["capital"] += d["buy_price"]
        out.append(d)
    stats["realised"] = round(stats["realised"], 2)
    return {"items": out, "stats": stats, "stages": STAGES}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj, ctype="application/json"):
        data = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") or ctype == "application/json" else ""))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def route(self, method):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path
        conn = db.connect()
        try:
            if not p.startswith("/api/"):
                f = os.path.normpath(os.path.join(STATIC, "index.html" if p == "/" else p.lstrip("/")))
                if not f.startswith(STATIC) or not os.path.isfile(f):
                    return self._send(404, {"error": "not found"})
                return self._send(200, open(f, "rb").read(), mimetypes.guess_type(f)[0] or "application/octet-stream")
            if method == "GET":
                if p == "/api/niches": return self._send(200, api_niches(conn, q))
                m = re.fullmatch(r"/api/niche/([\w-]+)/buys", p)
                if m: return self._send(200, api_buys(conn, m[1], q))
                m = re.fullmatch(r"/api/niche/([\w-]+)/sales", p)
                if m: return self._send(200, {"items": engine.sales_ranking(engine.Context(conn), m[1])[:10]})
                m = re.fullmatch(r"/api/listing/(\d+)", p)
                if m:
                    v = api_listing(conn, int(m[1]))
                    return self._send(200 if v else 404, v or {"error": "introuvable"})
                if p == "/api/settings": return self._send(200, db.get_settings(conn))
                if p == "/api/deals": return self._send(200, api_deals(conn))
                if p == "/api/sources":
                    c = conn.execute("SELECT source, COUNT(*) n, MAX(last_seen) last FROM listings GROUP BY source").fetchall()
                    return self._send(200, [dict(x) for x in c])
            if method == "POST":
                b = self._body()
                if p == "/api/settings":
                    db.set_settings(conn, b); return self._send(200, db.get_settings(conn))
                if p == "/api/analyze": return self._send(200, api_analyze(conn, b))
                if p == "/api/scan": return self._send(200, sources.run_scan(conn))
                if p == "/api/import":
                    items = sources.ManualImport.parse(b.get("text", ""))
                    counts = {"new": 0, "updated": 0, "unchanged": 0, "unrecognized": 0}
                    for d in items:
                        counts[sources.upsert(conn, d)] += 1
                        if not engine.match_product(f"{d['title']} {d.get('description','')}"):
                            counts["unrecognized"] += 1
                    conn.commit()
                    return self._send(200, {"parsed": len(items), **counts})
                m = re.fullmatch(r"/api/listing/(\d+)/ignore", p)
                if m:
                    conn.execute("UPDATE listings SET ignored=1 WHERE id=?", (int(m[1]),)); conn.commit()
                    return self._send(200, {"ok": True})
                if p == "/api/deals":
                    now = db.now()
                    title, est = b.get("title", ""), b.get("est_net")
                    conn.execute("INSERT INTO deals(listing_id,title,stage,est_net,buy_price,created,updated) VALUES(?,?,?,?,?,?,?)",
                                 (b.get("listing_id"), title, "repere", est, b.get("buy_price"), now, now))
                    conn.commit()
                    return self._send(200, api_deals(conn))
            if method == "PATCH":
                b = self._body()
                m = re.fullmatch(r"/api/deals/(\d+)", p)
                if m:
                    sets, vals = [], []
                    for k in ("stage", "buy_price", "sell_price", "notes"):
                        if k in b:
                            if k == "stage" and b[k] not in STAGES:
                                raise ValueError("étape invalide")
                            sets.append(f"{k}=?"); vals.append(b[k])
                    sets.append("updated=?"); vals += [db.now(), int(m[1])]
                    conn.execute(f"UPDATE deals SET {', '.join(sets)} WHERE id=?", vals); conn.commit()
                    return self._send(200, api_deals(conn))
                m = re.fullmatch(r"/api/niche/([\w-]+)", p)
                if m:
                    for k in ("fee_pct", "pack_cost", "prep_cost", "delivery_default", "enabled"):
                        if k in b:
                            conn.execute(f"UPDATE niches SET {k}=? WHERE slug=?", (float(b[k]), m[1]))
                    conn.commit()
                    return self._send(200, {"ok": True})
            if method == "DELETE":
                m = re.fullmatch(r"/api/deals/(\d+)", p)
                if m:
                    conn.execute("DELETE FROM deals WHERE id=?", (int(m[1]),)); conn.commit()
                    return self._send(200, api_deals(conn))
            return self._send(404, {"error": "route inconnue"})
        except (ValueError, KeyError) as e:
            self._send(400, {"error": str(e)})
        except Exception as e:  # noqa
            self._send(500, {"error": f"{type(e).__name__}: {e}"})
        finally:
            conn.close()

    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PATCH(self): self.route("PATCH")
    def do_DELETE(self): self.route("DELETE")


if __name__ == "__main__":
    if "--reseed" in sys.argv and os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    ensure_db().close()
    port = int(os.environ.get("PORT", 8000))
    print(f"FlipRadar sur http://localhost:{port}  (données de DÉMO tant qu'aucune source réelle n'est branchée)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
