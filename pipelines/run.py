"""Fetch public data for the dashboard.

Run: python -m pipelines.run news oil fx worldbank trade   (any subset; "all" for everything)
Env: CENSUS_API_KEY (recommended: without it Census allows about 500 calls a day),
     EIA_API_KEY, FRED_API_KEY.
Each job writes under data/raw/. A failing job is recorded and the others still run.
"""
import datetime as _dt
import json
import os
import sys

from marketdata import census, eia, fx, news, store, worldbank

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
JOBS = ("news", "oil", "fx", "worldbank", "trade")


def raw(name):
    return os.path.join(RAW, name)


def load_config():
    with open(os.path.join(ROOT, "config", "dashboard.json"), encoding="utf-8") as fh:
        return json.load(fh)


def start_date(cfg):
    return (_dt.date.today() - _dt.timedelta(days=cfg["daily_history_days"])).isoformat()


def job_news(cfg):
    items, errors = news.update(store.load(raw("news.json"), []), cfg["feeds"])
    store.save(raw("news.json"), items)
    if len(errors) == len(cfg["feeds"]):
        raise RuntimeError("every feed failed: " + "; ".join(errors))
    return errors  # partial feed failures are reported, not fatal


def job_oil(cfg):
    key = os.environ.get("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA_API_KEY is not set")
    stored = store.load(raw("oil.json"), {"brent": {}, "wti": {}})
    for k, v in eia.fetch_daily(key, start_date(cfg)).items():
        stored.setdefault(k, {}).update(v)
    store.save(raw("oil.json"), stored)


def job_fx(cfg):
    key = os.environ.get("FRED_API_KEY")
    problems = []
    for cur in cfg["fx"]:
        f = raw(f"fx_{cur}.json")
        if cur == "TRY":
            have = store.load(f, {})
            store.save(f, fx.fetch_tcmb_range(start_date(cfg), _dt.date.today().isoformat(), have=have))
        elif key:
            store.save(f, fx.fetch_fred(cur, key, start_date(cfg)))
        else:
            problems.append(f"{cur}: FRED_API_KEY is not set")
    if problems:
        raise RuntimeError("; ".join(problems))


def job_worldbank(cfg):
    store.save(raw("worldbank.json"), worldbank.fetch(cfg["worldbank_monthly_url"]))


def job_trade(cfg):
    key = os.environ.get("CENSUS_API_KEY") or None
    problems = []
    for group in cfg["trade_groups"]:
        for line in group["lines"]:
            for code in line["codes"]:
                f = raw(os.path.join("trade", f"{code}_{line['flow']}.json"))
                try:
                    store.save(f, census.update_series(store.load(f), line["flow"], code, key,
                                                       history_months=cfg["trade_history_months"]))
                except Exception as err:
                    problems.append(f"{code}: {err}")
    if problems:
        raise RuntimeError("; ".join(problems))


def main(argv):
    wanted = JOBS if not argv or "all" in argv else [a for a in argv if a in JOBS]
    cfg = load_config()
    status = store.load(raw("status.json"), {})
    failed = False
    for name in wanted:
        try:
            warnings = globals()[f"job_{name}"](cfg) or []
            status[name] = {"ok": True, "at": store.now_iso(), "warnings": warnings}
        except Exception as err:
            failed = True
            prev = status.get(name, {})
            status[name] = {"ok": False, "at": store.now_iso(), "error": str(err), "last_ok": prev.get("at") if prev.get("ok") else prev.get("last_ok")}
            print(f"ERROR {name}: {err}", file=sys.stderr)
    store.save(raw("status.json"), status)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
