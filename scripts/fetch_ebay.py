"""Collecte les annonces actives eBay.fr via l'API officielle Browse (gratuite, clés développeur requises).

Secrets : EBAY_CLIENT_ID, EBAY_CLIENT_SECRET (https://developer.ebay.com › Application Keys › Production).
Écrit docs/data/ebay.json. Les annonces absentes de 2 collectes de suite passent en « disparue » :
cela ne prouve PAS une vente (eBay ne donne pas les ventes conclues via l'API gratuite).
"""
import base64, json, os, sys, time, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "ebay.json")
QUERIES = json.load(open(os.path.join(os.path.dirname(__file__), "queries.json")))
MARKET = os.environ.get("EBAY_MARKETPLACE", "EBAY_FR")
FOR_PARTS = {7000}                      # conditionId « pour pièces »
NEW = {1000, 1500, 1750}                # neuf


def call(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def token(cid, secret):
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"}).encode()
    return call("https://api.ebay.com/identity/v1/oauth2/token", body,
                {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"})["access_token"]


def search(tok, q):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search?" + urllib.parse.urlencode(
        {"q": q, "limit": 50, "filter": "buyingOptions:{FIXED_PRICE},priceCurrency:EUR"})
    return call(url, headers={"Authorization": f"Bearer {tok}", "X-EBAY-C-MARKETPLACE-ID": MARKET}).get("itemSummaries", [])


def to_listing(it, key):
    price = it.get("price", {})
    if price.get("currency") != "EUR":
        return None
    try:
        p = float(price["value"])
    except Exception:
        return None
    cid = int(it.get("conditionId") or 0)
    ship = None
    try:
        ship = float(it["shippingOptions"][0]["shippingCost"]["value"])
    except Exception:
        pass
    seller = it.get("seller", {})
    fb = seller.get("feedbackPercentage")
    loc = it.get("itemLocation", {})
    return {"source": "ebay", "ext_id": it["itemId"], "url": it.get("itemWebUrl", "").split("?")[0], "title": it.get("title", "")[:200],
            "description": "pour pièces" if cid in FOR_PARTS else "", "price": p, "status": "", "product_key": key,
            "condition": "neuf" if cid in NEW else None, "location": f"{loc.get('postalCode','')} {loc.get('country','')}".strip(),
            "seller_rating": round(float(fb) / 20, 1) if fb else None, "seller_reviews": seller.get("feedbackScore"),
            "delivery_fee": ship}


def main():
    cid, sec = os.environ.get("EBAY_CLIENT_ID"), os.environ.get("EBAY_CLIENT_SECRET")
    if not cid or not sec:
        print("::warning::EBAY_CLIENT_ID / EBAY_CLIENT_SECRET absents : collecte ignorée (voir README)"); return
    try:
        db = {d["ext_id"]: d for d in json.load(open(OUT))}
    except Exception:
        db = {}
    tok, now, seen = token(cid, sec), int(time.time()), set()
    for q in QUERIES:
        try:
            items = search(tok, q["q"])
        except Exception as e:
            print(f"::warning::{q['q']} : {e}"); continue
        for it in items:
            l = to_listing(it, q["key"])
            if not l:
                continue
            seen.add(l["ext_id"]); old = db.get(l["ext_id"], {})
            db[l["ext_id"]] = {**old, **l, "first_seen": old.get("first_seen", now), "last_seen": now, "miss": 0}
        time.sleep(0.3)
    for k, d in db.items():
        if k in seen:
            d["status"] = ""
        elif d.get("status") != "disparue":
            d["miss"] = d.get("miss", 0) + 1
            if d["miss"] >= 2:
                d["status"] = "disparue"
    db = {k: d for k, d in db.items() if not (d.get("status") == "disparue" and now - d.get("last_seen", now) > 60 * 86400)}
    json.dump(sorted(db.values(), key=lambda d: -d["first_seen"]), open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"{len(seen)} annonces vues, {len(db)} en base")


if __name__ == "__main__":
    main()
