"""U.S. Census Bureau international trade API (monthly, by HS code and country).

Docs: https://api.census.gov/data/timeseries/intltrade/exports/hs/variables.html
Data appear roughly five weeks after the month ends. Census revises recent
months; the dashboard refreshes the last few months on every run, while the
index keeps the snapshot it used when a value was published.
"""
import time

from . import months as M
from . import net

BASE = "https://api.census.gov/data/timeseries/intltrade/{flow}/hs"

FIELDS = {
    "exports": {"code": "E_COMMODITY", "value": "ALL_VAL_MO", "qty": "QTY_1_MO", "unit": "UNIT_QY1"},
    "imports": {"code": "I_COMMODITY", "value": "GEN_VAL_MO", "qty": "GEN_QY1_MO", "unit": "UNIT_QY1"},
}


def comm_level(code):
    return {2: "HS2", 4: "HS4", 6: "HS6", 10: "HS10"}[len(code)]


def fetch_month(flow, code, month, api_key=None):
    """One commodity, one month, every partner country. Returns None when Census has no data."""
    f = FIELDS[flow]
    params = {
        "get": ",".join(["CTY_CODE", "CTY_NAME", f["value"], f["qty"], f["unit"]]),
        f["code"]: code,
        "COMM_LVL": comm_level(code),
        "time": month,
    }
    if api_key:
        params["key"] = api_key
    try:
        rows = net.get_json(BASE.format(flow=flow), params)
    except net.NoData:
        return None
    return parse_rows(rows, flow)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def parse_rows(rows, flow):
    """Census answers with a header row followed by data rows (all strings)."""
    if not rows or len(rows) < 2:
        return None
    f = FIELDS[flow]
    head = rows[0]
    ix = {name: head.index(name) for name in ("CTY_CODE", "CTY_NAME", f["value"], f["qty"], f["unit"])}
    total, countries, unit = None, {}, None
    for r in rows[1:]:
        code, name = r[ix["CTY_CODE"]], r[ix["CTY_NAME"]]
        value, qty = _num(r[ix[f["value"]]]), _num(r[ix[f["qty"]]])
        unit = unit or (r[ix[f["unit"]]] or None)
        if code == "-" or name.upper().startswith("TOTAL"):
            total = {"value": value, "qty": qty}
        elif code.isdigit() and int(code) >= 1000:  # 4-digit country codes; 0xxx are regional groupings
            countries[code] = {"name": name.title(), "value": value, "qty": qty}
    if total is None:
        total = {"value": sum(c["value"] for c in countries.values()),
                 "qty": sum(c["qty"] for c in countries.values())}
    return {"unit": unit, "value": total["value"], "qty": total["qty"], "countries": countries}


def update_series(series, flow, code, api_key=None, history_months=36, refresh_recent=3,
                  keep_countries=12, end=None):
    """Fill a stored series: backfill missing months, re-pull the most recent few (Census revises)."""
    series = series or {"code": code, "flow": flow, "unit": None, "months": {}}
    stored = series["months"]
    wanted = M.last_n(history_months, end)
    recent = set(wanted[-refresh_recent:])
    for month in wanted:
        if month in stored and month not in recent:
            continue
        t0 = time.time()
        got = fetch_month(flow, code, month, api_key)
        print(f"  {code} {month}: {'ok' if got else 'none'} ({time.time() - t0:.1f}s)", flush=True)
        if got is None:
            continue
        series["unit"] = series["unit"] or got["unit"]
        top = sorted(got["countries"].items(), key=lambda kv: -kv[1]["value"])[:keep_countries]
        stored[month] = {"value": got["value"], "qty": got["qty"], "countries": dict(top)}
    return series


def unit_value(months_data, month, window=1):
    """Value divided by quantity over `window` months ending at `month` (e.g. $/kg). None if unknown."""
    v = q = 0.0
    for m in M.span(M.add(month, -(window - 1)), month):
        rec = months_data.get(m)
        if not rec:
            return None
        v += rec["value"]
        q += rec["qty"]
    return v / q if q > 0 else None
