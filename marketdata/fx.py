"""Exchange rates, stored as units of foreign currency per U.S. dollar.

INR, BRL, THB: Federal Reserve H.10 noon rates, read through FRED (free key).
TRY: Central Bank of the Republic of Turkiye daily bulletin (no key). H.10 has no lira.
"""
import datetime as _dt
import time
import xml.etree.ElementTree as ET

from . import net

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"INR": "DEXINUS", "BRL": "DEXBZUS", "THB": "DEXTHUS"}
TCMB_DAY_URL = "https://www.tcmb.gov.tr/kurlar/{ym}/{dmy}.xml"


def fetch_fred(currency, api_key, start):
    payload = net.get_json(FRED_URL, {
        "series_id": FRED_SERIES[currency], "api_key": api_key,
        "file_type": "json", "observation_start": start,
    })
    return parse_fred(payload)


def parse_fred(payload):
    out = {}
    for obs in payload.get("observations", []):
        try:
            out[obs["date"]] = float(obs["value"])
        except (TypeError, ValueError):  # FRED writes "." for holidays
            continue
    return out


def parse_tcmb(xml_bytes):
    """USD ForexSelling (lira per dollar) from one daily bulletin."""
    root = ET.fromstring(xml_bytes)
    for cur in root.iter("Currency"):
        if cur.get("CurrencyCode") == "USD":
            txt = (cur.findtext("ForexSelling") or "").strip()
            return float(txt) if txt else None
    return None


def fetch_tcmb_range(start, end, have=None, pause=1.0, checkpoint=None, every=50, max_misses=6):
    """Daily lira rates for dates not already held. Weekends and holidays have no bulletin.

    Newest dates first, so a run cut short still has the recent months; `checkpoint(have)`
    is called every `every` fetches so progress survives a timeout."""
    have = dict(have or {})
    day = _dt.date.fromisoformat(end)
    stop = _dt.date.fromisoformat(start)
    done = misses = 0
    while day >= stop:
        iso = day.isoformat()
        if day.weekday() < 5 and iso not in have:
            url = TCMB_DAY_URL.format(ym=day.strftime("%Y%m"), dmy=day.strftime("%d%m%Y"))
            try:
                rate = parse_tcmb(net.get(url, timeout=20, retries=1))
                if rate:
                    have[iso] = rate
                misses = 0
            except net.NoData:
                misses = 0
            except Exception as err:
                # TCMB throttles bursts. Skip the day; stop (keeping progress) if it keeps refusing.
                misses += 1
                print(f"  TCMB: {iso} skipped ({err})", flush=True)
                if misses >= max_misses:
                    if checkpoint:
                        checkpoint(have)
                    raise RuntimeError(f"TCMB refused {misses} requests in a row; stopped at {iso}, progress saved") from None
                time.sleep(10 * misses)
            done += 1
            if checkpoint and done % every == 0:
                checkpoint(have)
                print(f"  TCMB: {done} days fetched, back to {iso}", flush=True)
            time.sleep(pause)
        day -= _dt.timedelta(days=1)
    return have


def monthly_average(daily):
    sums = {}
    for date, value in daily.items():
        m = date[:7]
        s, n = sums.get(m, (0.0, 0))
        sums[m] = (s + value, n + 1)
    return {m: s / n for m, (s, n) in sums.items()}
