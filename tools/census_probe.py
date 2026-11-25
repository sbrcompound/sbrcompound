"""One-off check of which Census trade queries return data. Prints a summary, never the key.
Run in CI: python -m tools.census_probe"""
import json, os, urllib.parse, urllib.request, urllib.error

KEY = os.environ.get("CENSUS_API_KEY", "")
M = "2026-09"
BASE = "https://api.census.gov/data/timeseries/intltrade/"

def q(path, params):
    p = dict(params, time=M)
    if KEY:
        p["key"] = KEY
    url = BASE + path + "?" + urllib.parse.urlencode(p, safe="*,")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            body = r.read()
            if r.status == 204 or not body:
                return "no data"
            rows = json.loads(body)
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:
        return f"error {type(e).__name__}: {str(e)[:120]}"
    head = rows[0]
    out = {"rows": len(rows) - 1, "cols": head}
    for k in ("ALL_VAL_MO", "QTY_1_MO", "GEN_VAL_MO", "GEN_QY1_MO"):
        if k in head:
            i = head.index(k)
            out[k] = sum(float(r[i] or 0) for r in rows[1:] if r[head.index("CTY_CODE")] in ("-", "")) if "CTY_CODE" in head else sum(float(r[i] or 0) for r in rows[1:])
    for k in ("E_COMMODITY", "I_COMMODITY"):
        if k in head:
            out["codes"] = sorted({r[head.index(k)] for r in rows[1:]})[:20]
    for k in ("STATE", "PORT_NAME"):
        if k in head:
            vi = head.index("ALL_VAL_MO")
            top = sorted(rows[1:], key=lambda r: -float(r[vi] or 0))[:8]
            out["top"] = [(r[head.index(k)], r[vi]) for r in top]
    return out

E = "exports/hs"; I = "imports/hs"
ex = lambda code, lvl: (E, {"get": "CTY_CODE,ALL_VAL_MO,QTY_1_MO,UNIT_QY1,E_COMMODITY", "E_COMMODITY": code, "COMM_LVL": lvl, "CTY_CODE": "-"})
im = lambda code, lvl: (I, {"get": "CTY_CODE,GEN_VAL_MO,GEN_QY1_MO,UNIT_QY1,I_COMMODITY", "I_COMMODITY": code, "COMM_LVL": lvl, "CTY_CODE": "-"})
TESTS = {
    "export 4004 scrap HS10": ex("4004000000", "HS10"),
    "export 4005.10 compound CB/silica": ex("4005100000", "HS10"),
    "export 4005.20 solutions": ex("4005200000", "HS10"),
    "export 4005.91 plates/sheets/strip": ex("4005910000", "HS10"),
    "export 4005.99 compound other": ex("4005990000", "HS10"),
    "export 4006.10 camelback": ex("4006100000", "HS10"),
    "export 4006.90 other unvulcanized forms": ex("4006900000", "HS10"),
    "export 5902 tire cord fabric HS4": ex("5902", "HS4"),
    "export 5902.10 HS10 wildcard": ex("590210*", "HS10"),
    "export 5906 rubberized fabric HS4": ex("5906", "HS4"),
    "export 4004 wildcard HS10": ex("4004*", "HS10"),
    "import 4001.21 wildcard HS10": im("400121*", "HS10"),
    "import 4001.22 wildcard HS10": im("400122*", "HS10"),
    "import 4002.19 wildcard HS10": im("400219*", "HS10"),
    "import 4001.22 HS6": im("400122", "HS6"),
    "export 4004 by state": ("exports/statehs", {"get": "STATE,ALL_VAL_MO,QTY_1_MO,E_COMMODITY", "E_COMMODITY": "400400", "COMM_LVL": "HS6"}),
    "export 4004 by port": ("exports/porths", {"get": "PORT,PORT_NAME,ALL_VAL_MO,E_COMMODITY", "E_COMMODITY": "400400", "COMM_LVL": "HS6"}),
    "export 4005 by state": ("exports/statehs", {"get": "STATE,ALL_VAL_MO,E_COMMODITY", "E_COMMODITY": "4005", "COMM_LVL": "HS4"}),
}
for name, (path, params) in TESTS.items():
    print(f"== {name}\n   {q(path, params)}", flush=True)
