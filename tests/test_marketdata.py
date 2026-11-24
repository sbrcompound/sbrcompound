"""Tests against the response shapes each source documents. Run: python -m unittest discover tests"""
import unittest

from marketdata import census, eia, fx, months, news, worldbank


class Months(unittest.TestCase):
    def test_add_and_span(self):
        self.assertEqual(months.add("2026-11", 2), "2027-01")
        self.assertEqual(months.add("2026-01", -1), "2025-12")
        self.assertEqual(months.span("2025-11", "2026-02"), ["2025-11", "2025-12", "2026-01", "2026-02"])


class Census(unittest.TestCase):
    ROWS = [
        ["CTY_CODE", "CTY_NAME", "ALL_VAL_MO", "QTY_1_MO", "UNIT_QY1", "E_COMMODITY", "COMM_LVL", "time"],
        ["-", "TOTAL FOR ALL COUNTRIES", "5000000", "4000000", "KG", "4004000000", "HS10", "2026-09"],
        ["0003", "EUROPEAN UNION", "900000", "700000", "KG", "4004000000", "HS10", "2026-09"],
        ["5330", "INDIA", "2000000", "1800000", "KG", "4004000000", "HS10", "2026-09"],
        ["4890", "TURKEY", "1000000", "700000", "KG", "4004000000", "HS10", "2026-09"],
    ]

    def test_parse_uses_total_row_and_skips_groupings(self):
        got = census.parse_rows(self.ROWS, "exports")
        self.assertEqual(got["value"], 5_000_000)
        self.assertEqual(got["unit"], "KG")
        self.assertEqual(set(got["countries"]), {"5330", "4890"})
        self.assertEqual(got["countries"]["5330"]["name"], "India")

    def test_unit_value_window(self):
        data = {"2026-08": {"value": 100.0, "qty": 50.0}, "2026-09": {"value": 300.0, "qty": 100.0}}
        self.assertAlmostEqual(census.unit_value(data, "2026-09", 2), 400 / 150)
        self.assertIsNone(census.unit_value(data, "2026-09", 3))


class WorldBank(unittest.TestCase):
    def test_parse_monthly_sheet(self):
        rows = [
            ("World Bank Commodity Price Data", None, None),
            (None, "Crude oil, Brent", "Rubber, TSR20 **", "Rubber, RSS3"),
            (None, "($/bbl)", "($/kg)", "($/kg)"),
            ("2026M03", 70.1, 2.01, 2.44),
            ("2026M04", 68.4, 2.06, 2.51),
        ]
        got = worldbank.parse_rows(rows)
        self.assertEqual(got["tsr20"]["months"]["2026-04"], 2.06)
        self.assertEqual(got["tsr20"]["unit"], "$/kg")
        self.assertEqual(got["brent"]["months"]["2026-03"], 70.1)
        self.assertNotIn("wti", got)


class Eia(unittest.TestCase):
    def test_parse(self):
        payload = {"response": {"data": [
            {"period": "2026-11-20", "series": "RBRTE", "value": "74.1"},
            {"period": "2026-11-20", "series": "RWTC", "value": 70.3},
            {"period": "2026-11-21", "series": "RWTC", "value": None},
        ]}}
        got = eia.parse(payload)
        self.assertEqual(got["brent"], {"2026-11-20": 74.1})
        self.assertEqual(got["wti"], {"2026-11-20": 70.3})


class Fx(unittest.TestCase):
    def test_fred_skips_missing(self):
        got = fx.parse_fred({"observations": [{"date": "2026-11-20", "value": "83.4"}, {"date": "2026-11-21", "value": "."}]})
        self.assertEqual(got, {"2026-11-20": 83.4})

    def test_tcmb(self):
        xml = b"""<?xml version="1.0"?><Tarih_Date><Currency CurrencyCode="USD"><ForexBuying>41.9</ForexBuying>
        <ForexSelling>41.98</ForexSelling></Currency><Currency CurrencyCode="EUR"><ForexSelling>48.1</ForexSelling></Currency></Tarih_Date>"""
        self.assertEqual(fx.parse_tcmb(xml), 41.98)

    def test_monthly_average(self):
        self.assertEqual(fx.monthly_average({"2026-10-01": 2.0, "2026-10-02": 4.0, "2026-11-03": 5.0}),
                         {"2026-10": 3.0, "2026-11": 5.0})


class News(unittest.TestCase):
    RSS = b"""<?xml version="1.0"?><rss><channel>
    <item><title>Tyre maker adds tariff surcharge</title><link>https://example.org/a</link>
    <pubDate>Mon, 23 Nov 2026 14:00:00 +0000</pubDate>
    <description>&lt;p&gt;The company said import duties raised costs.&lt;/p&gt;&lt;p&gt;The post &lt;a href="x"&gt;Tyre maker&lt;/a&gt; appeared first on &lt;a href="y"&gt;Tyrepress&lt;/a&gt;.&lt;/p&gt;</description></item>
    <item><title></title><link>https://example.org/b</link></item>
    </channel></rss>"""
    ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Pyrolysis plant opens</title>
    <link href="https://example.org/c"/><updated>2026-11-22T09:00:00Z</updated><summary>Recycling capacity grows.</summary></entry></feed>"""

    def test_rss_cleans_footer_and_tags(self):
        items = news.parse_feed(self.RSS, "Tyrepress")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["excerpt"], "The company said import duties raised costs.")
        self.assertEqual(items[0]["category"], "Trade policy")
        self.assertEqual(items[0]["published"], "2026-11-23T14:00:00Z")

    def test_atom(self):
        items = news.parse_feed(self.ATOM, "Example")
        self.assertEqual(items[0]["url"], "https://example.org/c")
        self.assertEqual(items[0]["category"], "Sustainability")


if __name__ == "__main__":
    unittest.main()
