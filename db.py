import os
import sqlite3
import time

DB_PATH = os.environ.get("FLIPRADAR_DB", os.path.join(os.path.dirname(__file__), "fliprad.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS niches(
  slug TEXT PRIMARY KEY, name TEXT, category TEXT, enabled INTEGER, safety INTEGER,
  fee_pct REAL, pack_cost REAL, prep_cost REAL, delivery_default REAL, note TEXT);
CREATE TABLE IF NOT EXISTS products(
  key TEXT PRIMARY KEY, niche TEXT, name TEXT, new_price REAL);
CREATE TABLE IF NOT EXISTS listings(
  id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, ext_id TEXT, url TEXT, title TEXT,
  description TEXT DEFAULT '', price REAL, status TEXT DEFAULT 'active', location TEXT DEFAULT '',
  condition TEXT DEFAULT 'bon', product_key TEXT, niche TEXT,
  seller_rating REAL, seller_reviews INTEGER, delivery_fee REAL, buyer_fee REAL DEFAULT 0,
  first_seen INTEGER, last_seen INTEGER, sold_at INTEGER, ignored INTEGER DEFAULT 0, demo INTEGER DEFAULT 0,
  UNIQUE(source, ext_id));
CREATE INDEX IF NOT EXISTS idx_l_prod ON listings(product_key, status);
CREATE TABLE IF NOT EXISTS snapshots(
  listing_id INTEGER, ts INTEGER, price REAL, status TEXT);
CREATE TABLE IF NOT EXISTS deals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER, title TEXT, stage TEXT DEFAULT 'repere',
  est_net REAL, buy_price REAL, sell_price REAL, notes TEXT DEFAULT '', created INTEGER, updated INTEGER);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""

DEFAULT_SETTINGS = {
    "buy_mode": "delivery",      # delivery | hand (main propre)
    "travel_cost": 3.0,          # coût de déplacement si main propre
    "min_margin": 15.0,          # marge nette minimale (€)
    "target_roi": 0.20,          # ROI visé pour le prix d'achat max
    "w_speed": 0.25,             # poids de la vitesse de vente dans le score
    "w_conf": 0.25,              # poids de la confiance des données
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def get_settings(conn):
    s = dict(DEFAULT_SETTINGS)
    for r in conn.execute("SELECT key, value FROM settings"):
        if r["key"] in s:
            s[r["key"]] = r["value"] if isinstance(s[r["key"]], str) else float(r["value"])
    return s


def set_settings(conn, data):
    for k, v in data.items():
        if k in DEFAULT_SETTINGS:
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, str(v)))
    conn.commit()


def now():
    return int(time.time())
