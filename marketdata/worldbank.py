"""World Bank Commodity Price Data ("Pink Sheet"), monthly historical workbook.

The workbook link changes when the World Bank starts a new year's document page.
If this fetch fails with a 404, open
https://www.worldbank.org/en/research/commodity-markets, copy the current link to
"CMO-Historical-Data-Monthly.xlsx", and paste it into the config file.
"""
import io
import re

from . import net

SERIES = {
    # key: prefix of the column header in the "Monthly Prices" sheet
    "tsr20": "Rubber, TSR20",
    "rss3": "Rubber, RSS3",
    "brent": "Crude oil, Brent",
    "wti": "Crude oil, WTI",
}

MONTH_RE = re.compile(r"^(\d{4})M(\d{2})$")


def fetch(url):
    import openpyxl  # installed in the workflow; kept local so other modules need nothing extra

    body = net.get(url, timeout=120)
    wb = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
    sheet = wb["Monthly Prices"]
    return parse_rows(list(sheet.iter_rows(values_only=True)))


def parse_rows(rows):
    """Find the header row, then read the wanted columns. Returns {key: {"unit", "months": {YYYY-MM: value}}}."""
    header_i = next(i for i, r in enumerate(rows) if r and any(isinstance(c, str) and c.startswith("Rubber") for c in r))
    header = rows[header_i]
    unit_row = rows[header_i + 1] if header_i + 1 < len(rows) else ()
    cols = {}
    for key, prefix in SERIES.items():
        for j, h in enumerate(header):
            if isinstance(h, str) and h.strip().startswith(prefix):
                unit = unit_row[j] if j < len(unit_row) else None
                cols[key] = (j, (unit or "").strip("() ") if isinstance(unit, str) else None)
                break
    out = {k: {"unit": u, "months": {}} for k, (_, u) in cols.items()}
    for r in rows[header_i + 1:]:
        if not r or not isinstance(r[0], str):
            continue
        m = MONTH_RE.match(r[0].strip())
        if not m:
            continue
        month = f"{m.group(1)}-{m.group(2)}"
        for key, (j, _) in cols.items():
            v = r[j] if j < len(r) else None
            if isinstance(v, (int, float)):
                out[key]["months"][month] = float(v)
    return out
