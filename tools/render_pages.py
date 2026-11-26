"""Wrap each page body in tools/pages/ with the shared header, tab bar and footer.
Run after editing a page: python tools/render_pages.py   (writes site/*.html)"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "site")
NAV = [("index", "Outlook", "/"), ("markets", "Markets", "/markets.html"), ("news", "News", "/news.html"), ("alerts", "Alerts", "/alerts.html")]
ICONS = {
  "index": '<path d="M4 15a8 8 0 0 1 16 0"/><path d="M12 15l4-5"/><circle cx="12" cy="15" r="1.4" fill="currentColor"/>',
  "markets": '<path d="M4 18l5-6 4 3 7-9"/><path d="M4 20h16"/>',
  "news": '<rect x="5" y="4" width="14" height="16" rx="2"/><path d="M9 9h6M9 13h6M9 17h3"/>',
  "alerts": '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
}
LOGO = ('<svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="4" fill="#f2b300"/>'
        '<rect x="5" y="7" width="22" height="18" rx="2" fill="#22201d"/>'
        '<path d="M10 7v18" stroke="#e0a400" stroke-width="3"/><path d="M15 7v18" stroke="#2c8a57" stroke-width="3"/>'
        '<path d="M20 7v18" stroke="#2d62d0" stroke-width="3"/></svg>')
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#22201d">
<meta name="color-scheme" content="light">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/assets/icons/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/icons/icon-180.png">
<link rel="preload" href="/assets/fonts/archivo-latin-wdth-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
<header class="topbar"><div class="wrap">
  <a class="logo" href="/">{logo}SBR Compound</a>
  <nav class="topnav" aria-label="Main"><ul>{topnav}</ul></nav>
</div><div class="batch" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div></header>
"""
FOOT = """<footer class="site-footer"><div class="wrap">
  <p>For information only. Not financial, legal or purchasing advice. Prices and trade figures come from public sources (U.S. Census Bureau, World Bank, U.S. Energy Information Administration, Federal Reserve, Central Bank of the Republic of Türkiye) and may be delayed or revised.</p>
  <p>SBR Compound is sponsored by <a href="https://www.carolinarecycle.com">Carolina Recycle Partners</a>, which buys and sells rubber compound. <a href="/privacy.html">Privacy</a></p>
</div></footer>
<nav class="tabbar" aria-label="Main">{tabs}</nav>
{scripts}
</body>
</html>
"""
def nav(current, tabs=False):
    out = []
    for key, label, href in NAV:
        cur = ' aria-current="page"' if key == current else ""
        if tabs:
            out.append(f'<a href="{href}"{cur}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[key]}</svg>{label}</a>')
        else:
            out.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    return "".join(out)
for fname in sorted(os.listdir(os.path.join(HERE, "pages"))):
    src = open(os.path.join(HERE, "pages", fname), encoding="utf-8").read()
    meta = dict(re.findall(r"^<!--\s*(\w+):\s*(.*?)\s*-->$", src, re.M))
    body = re.sub(r"^<!--.*?-->\n", "", src, flags=re.M)
    page = fname.replace(".html", "")
    scripts = "\n".join(f'<script src="{s}"></script>' for s in ["/assets/app.js"] + meta.get("scripts", "").split())
    html = HEAD.format(title=meta["title"], desc=meta["desc"], logo=LOGO, topnav=nav(meta.get("nav", page))) + body + FOOT.format(tabs=nav(meta.get("nav", page), True), scripts=scripts)
    open(os.path.join(SITE, fname), "w", encoding="utf-8").write(html)
    print("wrote", fname)
