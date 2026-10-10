import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["FLIPRADAR_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
import db, engine, seed, sources  # noqa: E402


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = db.connect(); db.init(cls.conn); seed.seed(cls.conn)

    def test_match(self):
        self.assertEqual(engine.match_product("PC portable Lenovo ThinkPad X395"), "tp-x395")
        self.assertEqual(engine.match_product("Perceuse Makita DHP 484 18V"), "makita-dhp484")
        self.assertEqual(engine.match_product("Lego 75192 neuf"), "lego-75192")
        self.assertIsNone(engine.match_product("Canapé 3 places"))
        self.assertNotEqual(engine.match_product("ThinkPad T480s"), "tp-t480")

    def test_condition(self):
        self.assertEqual(engine.detect_condition("Lego 75192 monté sans notice", "lego"), "degrade")
        self.assertEqual(engine.detect_condition("Lego neuf scellé", "lego"), "neuf")

    def test_risks(self):
        r = engine.detect_risks("vendu pour pièces, paypal ami famille", 40, 150, "pc-pro", 0, None)
        labels = " ".join(x["label"] for x in r)
        self.assertTrue(any(x["blocking"] for x in r))
        self.assertIn("hors plateforme", labels); self.assertIn("sans aucun avis", labels)

    def test_margin_math(self):
        ctx = engine.Context(self.conn)
        a = engine.analyze(ctx, {"id": None, "title": "ThinkPad T480", "description": "", "price": 100, "product_key": "tp-t480",
                                 "niche": "pc-pro", "condition": "bon", "seller_reviews": 20, "seller_rating": 4.8,
                                 "delivery_fee": 7.0, "buyer_fee": 2.0, "first_seen": db.now()})
        c = a["costs"]
        expected = a["resale"]["mid"] - c["resale_fee"] - c["packaging"] - c["prep"] - c["acquisition"]
        self.assertAlmostEqual(a["net"], expected, places=1)
        self.assertEqual(c["acquisition"], 109.0)
        self.assertEqual(a["resale"]["basis"], "observé")

    def test_import_status_badges(self):
        n = sources.ManualImport.parse("PC portable Lenovo ThinkPad X395;125;achat en cours;https://x/1;77420;bon;154")
        self.assertEqual(sources.upsert(self.conn, n[0]), "new")
        r = self.conn.execute("SELECT status, sold_at FROM listings WHERE ext_id='https://x/1'").fetchone()
        self.assertEqual(r["status"], "achat_en_cours"); self.assertIsNotNone(r["sold_at"])
        n[0]["status"] = "vendu"
        self.assertEqual(sources.upsert(self.conn, n[0]), "updated")

    def test_unknown_model_not_scored(self):
        a = engine.analyze(engine.Context(self.conn), {"title": "x", "price": 10, "product_key": None, "niche": None})
        self.assertFalse(a["analyzable"])


if __name__ == "__main__":
    unittest.main()
