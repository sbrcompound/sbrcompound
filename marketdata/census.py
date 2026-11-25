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
    """A trailing * asks Census for every 10-digit code under a prefix (e.g. 400122*)."""
    if code.endswith("*"):
        return "HS10"
    return {2: "HS2", 4: "HS4", 6: "HS6", 10: "HS10"}[len(code)]


def file_key(code):
    """Filesystem-safe name for a code that may carry a wildcard."""
    return code.replace("*", "x")


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
        # A wildcard query returns one row per 10-digit code, so add rows up rather than overwrite.
        if code == "-" or name.upper().startswith("TOTAL"):
            total = total or {"value": 0.0, "qty": 0.0}
            total["value"] += value
            total["qty"] += qty
        elif code.isdigit() and int(code) >= 1000:  # 4-digit country codes; 0xxx are regional groupings
            c = countries.setdefault(code, {"name": name.title(), "value": 0.0, "qty": 0.0})
            c["value"] += value
            c["qty"] += qty
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


PORT_FIELDS = {"exports": ("ALL_VAL_MO", "E_COMMODITY"), "imports": ("GEN_VAL_MO", "I_COMMODITY")}


def fetch_ports(flow, hs6, month, api_key=None):
    """Value by U.S. port (district of exit or entry) for one 6-digit code and month.
    Census reports port detail by value only. Returns {port_name: value} or None."""
    val, comm = PORT_FIELDS[flow]
    params = {"get": f"PORT,PORT_NAME,{val}", comm: hs6, "COMM_LVL": "HS6", "time": month}
    if api_key:
        params["key"] = api_key
    try:
        rows = net.get_json(BASE.format(flow=flow).replace("/hs", "/porths"), params)
    except net.NoData:
        return None
    if not rows or len(rows) < 2:
        return None
    head = rows[0]
    i_name, i_val = head.index("PORT_NAME"), head.index(val)
    out = {}
    for r in rows[1:]:
        name = r[i_name]
        if not name or name.upper().startswith("TOTAL"):
            continue
        out[name.title()] = out.get(name.title(), 0.0) + _num(r[i_val])
    return out


def update_ports(series, flow, hs6, api_key=None, months_back=12, end=None):
    """Keep the last `months_back` months of port detail, re-pulling the newest three."""
    series = series or {"hs6": hs6, "flow": flow, "months": {}}
    wanted = M.last_n(months_back, end)
    for month in wanted:
        if month in series["months"] and month not in wanted[-3:]:
            continue
        got = fetch_ports(flow, hs6, month, api_key)
        if got:
            series["months"][month] = got
    series["months"] = {m: v for m, v in series["months"].items() if m in wanted}
    return series

