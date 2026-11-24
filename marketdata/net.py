"""Small HTTP helper: retries, timeouts, and a polite User-Agent."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "public-market-data/1.0 (scheduled job; contact via site)"


class NoData(Exception):
    """The source answered but has nothing for this request (e.g. HTTP 204/404)."""


def build_url(url, params=None):
    if not params:
        return url
    query = urllib.parse.urlencode(params, doseq=True, safe=",[]")
    return url + ("&" if "?" in url else "?") + query


def get(url, params=None, timeout=60, retries=4, backoff=3.0):
    full = build_url(url, params)
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 204:
                    raise NoData(full)
                return resp.read()
        except NoData:
            raise
        except urllib.error.HTTPError as err:
            if err.code in (204, 404):
                raise NoData(f"{err.code} {redact(full)}") from None
            last_err = err
            if err.code < 500 and err.code != 429:
                raise RuntimeError(f"HTTP {err.code} for {redact(full)}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            last_err = err
        time.sleep(backoff * (2 ** attempt))
    raise RuntimeError(f"Gave up on {redact(full)}: {last_err}")


def get_json(url, params=None, **kw):
    body = get(url, params, **kw)
    if not body.strip():
        raise NoData(redact(build_url(url, params)))
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        snippet = body[:300].decode("utf-8", "replace").replace("\n", " ")
        raise RuntimeError(f"Not JSON from {redact(build_url(url, params))}: {snippet}") from None


def redact(url):
    """Hide API keys before a URL goes into a log."""
    parts = urllib.parse.urlsplit(url)
    qs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    clean = [(k, "***" if k.lower() in ("key", "api_key", "apikey") else v) for k, v in qs]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(clean)))
