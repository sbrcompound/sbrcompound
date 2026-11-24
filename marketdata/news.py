"""Industry news from publisher RSS/Atom feeds.

Only the headline, a short excerpt and the link are kept; readers click through
to the publisher for the article.
"""
import datetime as _dt
import email.utils
import html
import re
import xml.etree.ElementTree as ET

from . import net

ATOM = "{http://www.w3.org/2005/Atom}"
TAG_RE = re.compile(r"<[^>]+>")
FOOTER_RE = re.compile(r"The post .{0,300}? appeared first on .{0,120}?\.?\s*$", re.S)
WS_RE = re.compile(r"\s+")

CATEGORIES = [
    ("Trade policy", ["tariff", "duty", "duties", "anti-dumping", "antidumping", "trade", "import", "export",
                      "sanction", "customs", "section 232", "section 301"]),
    ("Feedstock costs", ["natural rubber", "synthetic rubber", "butadiene", "carbon black", "silica", "sbr",
                         "price", "prices", "feedstock", "latex", "crude", "oil"]),
    ("Sustainability", ["recycl", "circular", "end-of-life", "elt", "emission", "sustainab", "pyrolysis",
                        "reclaim", "devulcan", "eudr", "deforestation"]),
    ("Tire industry", ["tire", "tyre", "oem", "plant", "factory", "retread"]),
]


def clean_text(raw, limit=240):
    text = html.unescape(TAG_RE.sub(" ", raw or ""))
    text = WS_RE.sub(" ", text).strip()
    text = FOOTER_RE.sub("", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:-") + "…"
    return text


def categorize(title, excerpt):
    hay = f"{title} {excerpt}".lower()
    for name, words in CATEGORIES:
        if any(w in hay for w in words):
            return name
    return "Industry"


def _date(raw):
    if not raw:
        return None
    raw = raw.strip()
    try:
        return email.utils.parsedate_to_datetime(raw).astimezone(_dt.timezone.utc).isoformat()[:19] + "Z"
    except (TypeError, ValueError):
        pass
    return raw[:19] + "Z" if len(raw) >= 19 and raw[4] == "-" else None


def parse_feed(xml_bytes, source):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):  # RSS 2.0
        items.append({
            "title": clean_text(it.findtext("title"), 200),
            "url": (it.findtext("link") or "").strip(),
            "published": _date(it.findtext("pubDate")),
            "excerpt": clean_text(it.findtext("description")),
        })
    for it in root.iter(f"{ATOM}entry"):  # Atom
        link = it.find(f"{ATOM}link[@rel='alternate']")
        if link is None:
            link = it.find(f"{ATOM}link")
        items.append({
            "title": clean_text(it.findtext(f"{ATOM}title"), 200),
            "url": link.get("href", "").strip() if link is not None else "",
            "published": _date(it.findtext(f"{ATOM}published") or it.findtext(f"{ATOM}updated")),
            "excerpt": clean_text(it.findtext(f"{ATOM}summary") or it.findtext(f"{ATOM}content")),
        })
    out = []
    for item in items:
        if not item["title"] or not item["url"].startswith("http"):
            continue
        item["source"] = source
        item["category"] = categorize(item["title"], item["excerpt"])
        out.append(item)
    return out


def update(stored, feeds, keep=250):
    """Merge fresh items into the stored list, dedupe by link, newest first. Returns (items, errors)."""
    by_url = {i["url"]: i for i in (stored or [])}
    errors = []
    for feed in feeds:
        try:
            for item in parse_feed(net.get(feed["url"], retries=2), feed["name"]):
                by_url.setdefault(item["url"], item)
        except Exception as err:  # one broken feed must not stop the others
            errors.append(f"{feed['name']}: {err}")
    items = sorted(by_url.values(), key=lambda i: i.get("published") or "", reverse=True)
    return items[:keep], errors
