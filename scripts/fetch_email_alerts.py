"""Lit les alertes e-mail de recherches sauvegardées Leboncoin (IMAP) et met à jour docs/data/listings.json.

Aucune requête vers Leboncoin : on ne lit que VOTRE boîte mail (fonction officielle « alerte de recherche »).
Secrets requis (GitHub > Settings > Secrets and variables > Actions) :
  IMAP_USER, IMAP_PASSWORD (mot de passe d'application), optionnel IMAP_HOST (défaut imap.gmail.com).
Limite : un e-mail d'alerte ne contient pas les badges « Achat en cours » / « Vendu ».
"""
import email, imaplib, json, os, re, sys
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "listings.json")
SENDER = os.environ.get("ALERT_SENDER", "leboncoin")
DAYS = int(os.environ.get("ALERT_DAYS", "14"))


class Links(HTMLParser):
    """Liste ordonnée des textes + positions des liens d'annonces."""
    def __init__(self):
        super().__init__(); self.tokens, self.anchors, self._href, self._start = [], [], None, 0

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            h = dict(attrs).get("href", "")
            if re.search(r"\d{7,}", h) and ("leboncoin" in h or "/ad/" in h):
                self._href, self._start = h, len(self.tokens)

    def handle_data(self, data):
        t = data.strip()
        if t:
            self.tokens.append(t)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.anchors.append((self._href, self._start, len(self.tokens)))
            self._href = None


PRICE = re.compile(r"(\d[\d\s\u202f\u00a0]*(?:[.,]\d+)?)\s*€")


def parse_html(html, when):
    p = Links(); p.feed(html); out = []
    for k, (href, s, e) in enumerate(p.anchors):
        m = re.search(r"(\d{7,})", href)
        nxt = p.anchors[k + 1][1] if k + 1 < len(p.anchors) else len(p.tokens)
        own = [t for t in p.tokens[s:e]]
        pm = next((PRICE.search(t) for t in own + p.tokens[e:min(e + 6, nxt if nxt > e else e + 6)] if PRICE.search(t)), None)
        title = next((t for t in own if len(t) > 8 and not PRICE.fullmatch(t.strip())), "") or \
            next((t for t in p.tokens[max(0, s - 3):s] if len(t) > 12 and "€" not in t), "")
        title = PRICE.sub("", title).strip(" -–")
        if not (m and pm and title):
            continue
        out.append({"source": "email-alerte", "ext_id": m.group(1), "url": href.split("?")[0], "title": title[:200],
                    "price": float(re.sub(r"[\s\u202f\u00a0]", "", pm.group(1)).replace(",", ".")), "status": "",
                    "first_seen": int(when.timestamp())})
    return out


def main():
    user, pwd = os.environ.get("IMAP_USER"), os.environ.get("IMAP_PASSWORD")
    if not user or not pwd:
        sys.exit("IMAP_USER / IMAP_PASSWORD manquants (voir README)")
    try:
        db = {d["ext_id"]: d for d in json.load(open(OUT))}
    except Exception:
        db = {}
    M = imaplib.IMAP4_SSL(os.environ.get("IMAP_HOST", "imap.gmail.com")); M.login(user, pwd); M.select("INBOX", readonly=True)
    since = (datetime.utcnow() - timedelta(days=DAYS)).strftime("%d-%b-%Y")
    _, ids = M.search(None, f'(FROM "{SENDER}" SINCE {since})')
    n_mail = n_new = 0
    for i in ids[0].split():
        _, data = M.fetch(i, "(RFC822)"); msg = email.message_from_bytes(data[0][1]); n_mail += 1
        try:
            when = parsedate_to_datetime(msg["Date"])
        except Exception:
            when = datetime.utcnow()
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                for d in parse_html(html, when):
                    if d["ext_id"] not in db:
                        n_new += 1
                    db[d["ext_id"]] = {**db.get(d["ext_id"], {}), **d}
    M.logout()
    json.dump(sorted(db.values(), key=lambda d: -d["first_seen"]), open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"{n_mail} e-mails lus, {n_new} nouvelles annonces, {len(db)} au total")


if __name__ == "__main__":
    main()
