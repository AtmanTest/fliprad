"""Moteur d'analyse : normalisation, valorisation, marge nette, risques, score.

Principe : tout chiffre est traçable. La valeur de revente vient en priorité des
VENTES OBSERVÉES (badges « Vendu » / « Achat en cours »), sinon elle est marquée
« estimé » avec une confiance basse.
"""
import re
import statistics
import time
import unicodedata

from catalog import COND_FACTOR, COND_LABEL, PRODUCTS
import db

SOLD_STATUSES = ("vendu", "achat_en_cours")
WINDOW_DAYS = 120


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


_PATTERNS = [(p[0], [re.compile(x) for x in p[3]]) for p in PRODUCTS]
_BY_KEY = {p[0]: p for p in PRODUCTS}


def match_product(text):
    t = norm(text)
    for key, pats in _PATTERNS:
        if any(p.search(t) for p in pats):
            return key
    return None


def product_niche(key):
    return _BY_KEY[key][1] if key in _BY_KEY else None


def detect_condition(text, niche):
    t = norm(text)
    if niche == "lego":
        if re.search(r"incomplet|manque|sans notice|sans boite|vrac|monte|deballe|ouvert", t) and "jamais ouvert" not in t:
            return "degrade"
        return "neuf"
    if re.search(r"neuf|scelle|jamais utilise|sous blister", t):
        return "neuf"
    if re.search(r"incomplet|rayure|marque|abime|usure|use|etat correct|bon etat general", t) and "tres bon etat" not in t:
        return "use"
    if re.search(r"degrade|casse", t):
        return "degrade"
    return "bon"


BLOCKING = r"pour pieces|hors service|\bhs\b|ne demarre|ne s allume|ne fonctionne pas|en panne|casse|fissure|a reparer|icloud|bloque|verrouille par"
OFF_PLATFORM = r"paypal|western union|mandat|virement|whatsapp|hors leboncoin|lien de paiement|ami famille"


def detect_risks(text, price, median, niche, reviews, rating):
    """-> liste de {label, weight, blocking}. weight = part de risque (0-1)."""
    t = norm(text)
    out = []
    if re.search(BLOCKING, t):
        out.append({"label": "Défaut ou blocage déclaré (pièces / HS / verrou)", "weight": 0.5, "blocking": True})
    if re.search(OFF_PLATFORM, t):
        out.append({"label": "Paiement ou contact hors plateforme : arnaque probable", "weight": 0.4, "blocking": False})
    if median and price and price < 0.55 * median:
        out.append({"label": "Prix très inférieur au marché : arnaque ou défaut caché possible", "weight": 0.25, "blocking": False})
    if reviews is not None and reviews == 0:
        out.append({"label": "Vendeur sans aucun avis", "weight": 0.10, "blocking": False})
    elif rating is not None and reviews and reviews >= 5 and rating < 4.0:
        out.append({"label": f"Vendeur mal noté ({rating:.1f}/5)", "weight": 0.10, "blocking": False})
    if niche == "pc-pro":
        if re.search(r"bios|mot de passe|mdm|compte administrateur|verrou", t):
            out.append({"label": "Verrou BIOS / MDM possible : à vérifier avant achat", "weight": 0.30, "blocking": False})
        if re.search(r"batterie (hs|usee|faible|a changer)", t):
            out.append({"label": "Batterie à remplacer (coût à prévoir)", "weight": 0.15, "blocking": False})
        if "sans chargeur" in t:
            out.append({"label": "Sans chargeur (≈ 15–25 € à ajouter)", "weight": 0.05, "blocking": False})
    if niche == "lego" and re.search(r"boite abimee|boite ecrasee|coin ecrase", t):
        out.append({"label": "Boîte abîmée : revente un peu plus basse", "weight": 0.05, "blocking": False})
    if niche == "lego" and re.search(r"replica|compatible|type lego|moc\b", t):
        out.append({"label": "Contrefaçon / compatible possible", "weight": 0.5, "blocking": True})
    return out


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _pct(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    i = (len(vals) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (i - lo)


class Context:
    """Données agrégées par modèle, calculées une fois par requête."""

    def __init__(self, conn):
        self.conn = conn
        self.settings = db.get_settings(conn)
        self.now = db.now()
        self.niches = {r["slug"]: dict(r) for r in conn.execute("SELECT * FROM niches")}
        self.sold = {}      # key -> [dict]
        self.active = {}    # key -> [prix normalisés]
        horizon = self.now - WINDOW_DAYS * 86400
        for r in conn.execute("SELECT * FROM listings WHERE product_key IS NOT NULL AND price > 0"):
            f = COND_FACTOR.get(r["condition"], 0.88)
            if r["status"] in SOLD_STATUSES and r["sold_at"] and r["sold_at"] >= horizon:
                self.sold.setdefault(r["product_key"], []).append({
                    "id": r["id"], "price": r["price"], "norm": r["price"] / f, "status": r["status"],
                    "days": max(0.0, (r["sold_at"] - r["first_seen"]) / 86400), "sold_at": r["sold_at"],
                    "condition": r["condition"]})
            elif r["status"] == "active" and not r["ignored"]:
                self.active.setdefault(r["product_key"], []).append(r["price"] / f)

    def stats(self, key):
        s = self.sold.get(key, [])
        a = self.active.get(key, [])
        norms = [x["norm"] for x in s]
        n = len(s)
        recent30 = [x for x in s if x["sold_at"] >= self.now - 30 * 86400]
        return {
            "n": n, "n_vendu": sum(1 for x in s if x["status"] == "vendu"),
            "median": statistics.median(norms) if norms else None,
            "p25": _pct(norms, 0.25), "p75": _pct(norms, 0.75),
            "days": statistics.median([x["days"] for x in s]) if s else None,
            "sold30": len(recent30), "sold90": sum(1 for x in s if x["sold_at"] >= self.now - 90 * 86400),
            "active_n": len(a), "active_median": statistics.median(a) if a else None,
            "active_p25": _pct(a, 0.25),
            "confidence": "haute" if n >= 10 else "moyenne" if n >= 4 else "basse",
        }


def valuation(ctx, key, cond):
    """-> dict(mid, low, high, basis, label, n, confidence) ou None."""
    st = ctx.stats(key)
    f = COND_FACTOR.get(cond, 0.88)
    new_price = _BY_KEY[key][4]
    if st["n"] >= 3:
        return {"mid": st["median"] * f, "low": st["p25"] * f, "high": st["p75"] * f, "basis": "observé",
                "label": f"{st['n']} ventes observées (badges Vendu / Achat en cours), 120 j",
                "n": st["n"], "confidence": st["confidence"]}
    if st["active_n"] >= 3:
        m = st["active_median"] * 0.9 * f
        return {"mid": m, "low": m * 0.9, "high": m * 1.1, "basis": "estimé",
                "label": f"Estimé : médiane des {st['active_n']} annonces actives −10 % (aucune vente observée)",
                "n": 0, "confidence": "basse"}
    if new_price:
        m = new_price * 0.6 * f
        return {"mid": m, "low": m * 0.85, "high": m * 1.15, "basis": "estimé",
                "label": "Estimé : 60 % du prix neuf indicatif (très peu de données)", "n": 0, "confidence": "basse"}
    return None


def acquisition(ctx, listing, niche):
    s = ctx.settings
    extra = listing["buyer_fee"] or 0.0
    if s["buy_mode"] == "delivery":
        d = listing["delivery_fee"] if listing["delivery_fee"] is not None else niche["delivery_default"]
    else:
        d = s["travel_cost"]
    return listing["price"], extra, d


def max_buy(ctx, resale, niche):
    s = ctx.settings
    sell_net = resale * (1 - niche["fee_pct"] / 100.0) - niche["pack_cost"] - niche["prep_cost"]
    extras = niche["delivery_default"] if s["buy_mode"] == "delivery" else s["travel_cost"]
    base = sell_net - extras
    return max(0.0, min(base / (1 + s["target_roi"]), base - s["min_margin"]))


def analyze(ctx, listing):
    """Analyse complète d'une annonce (sqlite Row ou dict)."""
    listing = dict(listing)
    key = listing.get("product_key")
    niche = ctx.niches.get(listing.get("niche")) if listing.get("niche") else None
    res = {"id": listing.get("id"), "analyzable": False}
    if not key or not niche:
        res["reason"] = "Modèle non reconnu dans le catalogue"
        return res
    cond = listing.get("condition") or "bon"
    val = valuation(ctx, key, cond)
    if not val:
        res["reason"] = "Pas assez de données pour valoriser ce modèle"
        return res
    st = ctx.stats(key)
    price, buyer_fee, delivery = acquisition(ctx, listing, niche)
    acq = price + buyer_fee + delivery
    fee = val["mid"] * niche["fee_pct"] / 100.0
    net = val["mid"] - fee - niche["pack_cost"] - niche["prep_cost"] - acq
    roi = net / acq if acq else 0.0
    risks = detect_risks(f"{listing.get('title','')} {listing.get('description','')}", price, val["mid"],
                         niche["slug"], listing.get("seller_reviews"), listing.get("seller_rating"))
    risk = clamp(sum(r["weight"] for r in risks), 0, 0.8)
    blocking = any(r["blocking"] for r in risks)
    days = st["days"] if st["days"] is not None else 30.0
    s = ctx.settings
    margin_c = clamp(roi / 0.35)
    if net < s["min_margin"]:
        margin_c *= clamp(net / s["min_margin"]) if net > 0 else 0
    speed_c = clamp(1 - days / 45.0)
    conf_c = {"haute": 1.0, "moyenne": 0.6, "basse": 0.3}[val["confidence"]]
    if val["basis"] == "estimé":
        conf_c = min(conf_c, 0.25)
    base = max(0.0, 1 - s["w_speed"] - s["w_conf"])
    score = 100 * margin_c * (base + s["w_speed"] * speed_c + s["w_conf"] * conf_c) * (1 - risk)
    mb = max_buy(ctx, val["mid"], niche)
    age = (ctx.now - (listing.get("first_seen") or ctx.now)) / 86400
    offer = min(price, round(mb)) if mb > 0 else None
    why = [
        f"Revente estimée {val['mid']:.0f} € ({val['basis']}) — {val['label']}.",
        f"Coût total d'acquisition {acq:.0f} € (prix {price:.0f} + frais {buyer_fee:.2f} + livraison/déplacement {delivery:.2f}), "
        f"frais de revente et préparation {fee + niche['pack_cost'] + niche['prep_cost']:.0f} € → marge nette {net:.0f} € ({roi*100:.0f} %).",
        (f"Vend en ~{days:.0f} j (médiane observée), " if st["days"] is not None else "Délai de vente inconnu (30 j supposés), ")
        + (f"{len(risks)} risque(s) relevé(s)." if risks else "aucun risque détecté."),
    ]
    res.update({
        "analyzable": True, "product": {"key": key, "name": _BY_KEY[key][2]}, "niche": niche["slug"],
        "condition": cond, "condition_label": COND_LABEL.get(cond, cond),
        "resale": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in val.items()},
        "costs": {"price": price, "buyer_fee": buyer_fee, "delivery": delivery, "acquisition": round(acq, 2),
                  "resale_fee": round(fee, 2), "packaging": niche["pack_cost"], "prep": niche["prep_cost"]},
        "net": round(net, 2), "roi": round(roi, 3), "days_to_sell": round(days, 1) if st["days"] is not None else None,
        "score": round(score, 1), "risk": round(risk, 2), "risks": risks, "blocking": blocking,
        "max_buy": round(mb, 2), "offer": offer, "age_days": round(age, 1),
        "confidence": val["confidence"], "why": why,
        "message": (f"Bonjour, votre annonce « {listing.get('title','')} » est-elle toujours disponible ? "
                    f"Je suis intéressé et peux vous proposer {offer} € avec paiement via la plateforme. Cordialement.")
        if offer else None,
    })
    return res


def sales_ranking(ctx, niche_slug):
    """Top ventes : modèles qui se revendent le mieux dans la niche."""
    niche = ctx.niches[niche_slug]
    rows = []
    for p in PRODUCTS:
        if p[1] != niche_slug:
            continue
        key = p[0]
        st = ctx.stats(key)
        if st["n"] == 0 and st["active_n"] == 0:
            continue
        val = valuation(ctx, key, "bon" if niche_slug == "pc-pro" else "neuf" if niche_slug == "lego" else "bon")
        if not val:
            continue
        mid = val["mid"]
        mb = max_buy(ctx, mid, niche)
        ask = st["active_p25"] * COND_FACTOR["neuf" if niche_slug == "lego" else "bon"] if st["active_p25"] else mid * 0.85
        acq = ask + (niche["delivery_default"] if ctx.settings["buy_mode"] == "delivery" else ctx.settings["travel_cost"])
        net = mid * (1 - niche["fee_pct"] / 100) - niche["pack_cost"] - niche["prep_cost"] - acq
        roi = net / acq if acq else 0
        days = st["days"] if st["days"] is not None else 30.0
        speed = clamp(1 - days / 45.0)
        vol = clamp(st["sold30"] / 8.0)
        sale_rate = st["sold30"] / (st["sold30"] + st["active_n"]) if (st["sold30"] + st["active_n"]) else 0
        conf = {"haute": 1.0, "moyenne": 0.75, "basse": 0.4}[val["confidence"]] if val["basis"] == "observé" else 0.3
        score = 100 * (0.4 * speed + 0.3 * vol + 0.3 * clamp(roi / 0.35)) * conf
        rows.append({
            "key": key, "name": p[2], "score": round(score, 1), "basis": val["basis"], "confidence": val["confidence"],
            "sold30": st["sold30"], "sold90": st["sold90"], "n_vendu_confirme": st["n_vendu"],
            "days_to_sell": round(st["days"], 1) if st["days"] is not None else None,
            "median_sold": round(mid, 2), "p25": round(val["low"], 2), "p75": round(val["high"], 2),
            "active_n": st["active_n"], "ask_p25": round(ask, 2), "net_at_ask": round(net, 2),
            "roi": round(roi, 3), "max_buy": round(mb, 2), "sale_rate": round(sale_rate, 2),
        })
    rows.sort(key=lambda r: -r["score"])
    return rows


def niche_safety_measured(ctx, niche_slug):
    """Score de sûreté mesuré : faible dispersion des prix + bon taux de vente."""
    disp, rate = [], []
    for p in PRODUCTS:
        if p[1] != niche_slug:
            continue
        st = ctx.stats(p[0])
        if st["n"] >= 4 and st["median"]:
            disp.append((st["p75"] - st["p25"]) / st["median"])
        tot = st["sold30"] + st["active_n"]
        if tot:
            rate.append(st["sold30"] / tot)
    if not disp:
        return None
    d = sum(disp) / len(disp)
    r = sum(rate) / len(rate) if rate else 0
    return round(100 * (0.6 * (1 - clamp(d / 0.4)) + 0.4 * clamp(r / 0.5)))
