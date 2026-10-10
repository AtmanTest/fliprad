"""Prix de VENTE réels des sets LEGO neufs via l'API officielle BrickLink (price guide « sold », 6 mois, Europe).

Secrets : BRICKLINK_CONSUMER_KEY, BRICKLINK_CONSUMER_SECRET, BRICKLINK_TOKEN, BRICKLINK_TOKEN_SECRET
(https://www.bricklink.com/v2/api/register_consumer.page ; IP autorisée : 0.0.0.0 pour GitHub Actions).
Écrit docs/data/bricklink.json : {product_key: {avg, p25, p75, min, max, n, source, updated}}.
"""
import base64, hashlib, hmac, json, os, re, secrets, time, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "bricklink.json")
QUERIES = [q for q in json.load(open(os.path.join(os.path.dirname(__file__), "queries.json"))) if q["niche"] == "lego"]
BASE = "https://api.bricklink.com/api/store/v1"
enc = lambda s: urllib.parse.quote(str(s), safe="~")


def signed_get(path, params, env):
    url = BASE + path
    oauth = {"oauth_consumer_key": env["BRICKLINK_CONSUMER_KEY"], "oauth_token": env["BRICKLINK_TOKEN"], "oauth_nonce": secrets.token_hex(8),
             "oauth_timestamp": str(int(time.time())), "oauth_signature_method": "HMAC-SHA1", "oauth_version": "1.0"}
    allp = {**params, **oauth}
    norm = "&".join(f"{enc(k)}={enc(v)}" for k, v in sorted(allp.items()))
    base = "&".join(["GET", enc(url), enc(norm)])
    key = f"{enc(env['BRICKLINK_CONSUMER_SECRET'])}&{enc(env['BRICKLINK_TOKEN_SECRET'])}"
    oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    header = 'OAuth realm="", ' + ", ".join(f'{k}="{enc(v)}"' for k, v in oauth.items())
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"Authorization": header})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def wpct(details, q):
    """Quantile pondéré par la quantité vendue."""
    pts = sorted((float(d["unit_price"]), int(d["quantity"])) for d in details)
    tot = sum(n for _, n in pts); acc = 0
    for p, n in pts:
        acc += n
        if acc >= q * tot:
            return p
    return pts[-1][0] if pts else None


def main():
    names = ["BRICKLINK_CONSUMER_KEY", "BRICKLINK_CONSUMER_SECRET", "BRICKLINK_TOKEN", "BRICKLINK_TOKEN_SECRET"]
    env = {n: os.environ.get(n) for n in names}
    if not all(env.values()):
        print("::warning::Secrets BrickLink absents : collecte ignorée (voir README)"); return
    try:
        out = json.load(open(OUT))
    except Exception:
        out = {}
    for q in QUERIES:
        num = re.search(r"\d{5}", q["key"]).group(0)
        try:
            r = signed_get(f"/items/SET/{num}-1/price", {"guide_type": "sold", "new_or_used": "N", "region": "europe", "currency_code": "EUR"}, env)
            d = r["data"]; det = d.get("price_detail", [])
            n = int(d.get("total_quantity") or 0)
            if not n:
                continue
            out[q["key"]] = {"avg": float(d["qty_avg_price"]), "min": float(d["min_price"]), "max": float(d["max_price"]),
                             "p25": wpct(det, .25), "p75": wpct(det, .75), "n": n,
                             "source": "BrickLink, ventes neuf 6 mois, Europe", "updated": int(time.time())}
        except Exception as e:
            print(f"::warning::{q['key']} : {e}")
        time.sleep(0.5)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"{len(out)} sets avec prix vendus")


if __name__ == "__main__":
    main()
