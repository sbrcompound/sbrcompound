"""U.S. Energy Information Administration: daily Brent and WTI spot prices ($/barrel).

Source attribution required: "U.S. Energy Information Administration (EIA)".
"""
from . import net

URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
SERIES = {"brent": "RBRTE", "wti": "RWTC"}


def fetch_daily(api_key, start):
    params = {
        "api_key": api_key,
        "frequency": "daily",
        "data[0]": "value",
        "facets[series][]": list(SERIES.values()),
        "start": start,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }
    return parse(net.get_json(URL, params))


def parse(payload):
    by_code = {v: k for k, v in SERIES.items()}
    out = {k: {} for k in SERIES}
    for row in payload.get("response", {}).get("data", []):
        key = by_code.get(row.get("series"))
        try:
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        if key:
            out[key][row["period"]] = value
    return out
