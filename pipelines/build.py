"""Turn data/raw/* into the small JSON files the website reads (site/data/).

Run: python -m pipelines.build
Only published, public numbers go into site/data. Missing inputs become nulls,
and the site shows "Data pending" for them rather than inventing a value.
"""
import datetime as _dt
import os
import statistics

from marketdata import months as M
from marketdata import store

from .run import RAW, ROOT, load_config, raw

SITE_DATA = os.path.join(ROOT, "site", "data")
UNIT_NAMES = {"KG": "kg", "NO": "tire", "T": "metric ton", "X": None}


def pct(a, b):
    return None if a is None or not b else round((a / b - 1) * 100, 2)


def monthly_block(series, keep=36):
    ms = sorted(series)
    if not ms:
        return None
    last = ms[-1]
    prev = series.get(M.add(last, -1))
    return {
        "latest": {"month": last, "value": series[last]},
        "change_pct": pct(series[last], prev),
        "series": [[m, round(series[m], 4)] for m in ms[-keep:]],
    }


def daily_block(series, keep=365):
    ds = sorted(series)
    if not ds:
        return None
    last = ds[-1]
    target = (_dt.date.fromisoformat(last) - _dt.timedelta(days=30)).isoformat()
    earlier = [d for d in ds if d <= target]
    base = series[earlier[-1]] if earlier else None
    return {
        "latest": {"date": last, "value": series[last]},
        "change_30d_pct": pct(series[last], base),
        "series": [[d, round(series[d], 4)] for d in ds[-keep:]],
    }


def combine(line):
    """Sum several Census codes into one line, month by month (only months every code reports)."""
    parts = [store.load(raw(os.path.join("trade", f"{c}_{line['flow']}.json"))) for c in line["codes"]]
    if not all(parts):
        return None, None
    unit = parts[0].get("unit")
    common = set(parts[0]["months"])
    for p in parts[1:]:
        common &= set(p["months"])
    out = {}
    for m in common:
        rec = {"value": 0.0, "qty": 0.0, "countries": {}}
        for p in parts:
            src = p["months"][m]
            rec["value"] += src["value"]
            rec["qty"] += src["qty"]
            for code, c in src.get("countries", {}).items():
                tgt = rec["countries"].setdefault(code, {"name": c["name"], "value": 0.0, "qty": 0.0})
                tgt["value"] += c["value"]
                tgt["qty"] += c["qty"]
        out[m] = rec
    return out, unit


def trade_line(line):
    data, unit = combine(line)
    if not data:
        return None, None
    ms = sorted(data)
    last = ms[-1]
    prior = [data[m]["qty"] for m in M.span(M.add(last, -12), M.add(last, -1)) if m in data]
    avg12 = statistics.fmean(prior) if len(prior) >= 6 else None
    uv_unit = UNIT_NAMES.get(unit, (unit or "").lower() or None)

    def uv(rec):
        return round(rec["value"] / rec["qty"], 4) if rec["qty"] > 0 and uv_unit else None

    summary = {
        "id": line["id"], "label": line["label"], "hts": line["hts"], "flow": line["flow"],
        "unit": uv_unit, "latest_month": last, "qty": data[last]["qty"], "value": data[last]["value"],
        "qty_vs_12m_pct": pct(data[last]["qty"], avg12), "unit_value": uv(data[last]),
        "spark": [[m, data[m]["qty"]] for m in ms[-24:]],
    }
    total = data[last]["value"] or 1
    detail = {
        **{k: summary[k] for k in ("id", "label", "hts", "flow", "unit", "latest_month")},
        "months": [{"month": m, "qty": data[m]["qty"], "value": data[m]["value"], "unit_value": uv(data[m])} for m in ms],
        "countries": sorted(
            [{"name": c["name"], "value": c["value"], "qty": c["qty"], "share_pct": round(c["value"] / total * 100, 1)}
             for c in data[last]["countries"].values()],
            key=lambda c: -c["value"])[:10],
    }
    return summary, detail


def scrap_factor(cfg):
    line = cfg["trade_groups"][0]["lines"][0]
    data, unit = combine(line)
    if not data or unit != "KG":
        return None
    last = max(data)

    def uv3(end):
        ms = M.span(M.add(end, -2), end)
        if not all(m in data for m in ms):
            return None
        q = sum(data[m]["qty"] for m in ms)
        return sum(data[m]["value"] for m in ms) / q if q else None

    now, year_ago = uv3(last), uv3(M.add(last, -12))
    return None if now is None else {"value": round(now, 3), "unit": "$/kg", "month": last,
                                     "change_yoy_pct": pct(now, year_ago)}


def build():
    cfg = load_config()
    wb = store.load(raw("worldbank.json"), {})
    oil = store.load(raw("oil.json"), {})
    status = store.load(raw("status.json"), {})

    rubber = {k: monthly_block(wb.get(k, {}).get("months", {})) for k in ("tsr20", "rss3")}
    oil_out = {k: daily_block(oil.get(k, {})) for k in ("brent", "wti")}
    fx_out = {}
    for cur, meta in cfg["fx"].items():
        blk = daily_block(store.load(raw(f"fx_{cur}.json"), {}))
        if blk:
            # A currency that buys more dollars than 30 days ago has strengthened.
            ch = blk["change_30d_pct"]
            blk["strength_30d_pct"] = None if ch is None else round((1 / (1 + ch / 100) - 1) * 100, 2)
        fx_out[cur] = dict(blk or {}, country=meta["country"]) if blk else {"country": meta["country"]}

    groups, latest_months = [], []
    os.makedirs(os.path.join(SITE_DATA, "trade"), exist_ok=True)
    for g in cfg["trade_groups"]:
        rows = []
        for line in g["lines"]:
            summary, detail = trade_line(line)
            if summary:
                rows.append(summary)
                latest_months.append(summary["latest_month"])
                store.save(os.path.join(SITE_DATA, "trade", f"{line['id']}.json"), detail)
            else:
                rows.append({k: line[k] for k in ("id", "label", "hts", "flow")})
        groups.append({"name": g["name"], "lines": rows})

    items = store.load(raw("news.json"), [])
    cutoff = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=30)).isoformat()[:19]
    policy = [i for i in items if i["category"] == "Trade policy" and (i.get("published") or "") >= cutoff]

    dashboard = {
        "generated": store.now_iso(),
        "jobs": {k: {"ok": v.get("ok"), "at": v.get("at") if v.get("ok") else v.get("last_ok")} for k, v in status.items()},
        "rubber": rubber,
        "oil": oil_out,
        "fx": fx_out,
        "trade": {"asof_month": max(latest_months) if latest_months else None, "groups": groups},
        "factors": {
            "scrap": scrap_factor(cfg),
            "virgin": rubber["tsr20"] and {"value": rubber["tsr20"]["latest"]["value"], "unit": "$/kg",
                                           "month": rubber["tsr20"]["latest"]["month"], "change_pct": rubber["tsr20"]["change_pct"]},
            "energy": oil_out["brent"] and {"value": oil_out["brent"]["latest"]["value"], "unit": "$/bbl",
                                             "date": oil_out["brent"]["latest"]["date"], "change_30d_pct": oil_out["brent"]["change_30d_pct"]},
            "policy": {"count_30d": len(policy), "latest": policy[:2]} if items else None,
        },
    }
    store.save(os.path.join(SITE_DATA, "dashboard.json"), dashboard)
    store.save(os.path.join(SITE_DATA, "news.json"), {"generated": dashboard["generated"], "items": items[:150]})
    if not os.path.exists(os.path.join(SITE_DATA, "outlook.json")):
        store.save(os.path.join(SITE_DATA, "outlook.json"), {"status": "pending"})
    return dashboard


if __name__ == "__main__":
    build()
