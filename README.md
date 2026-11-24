# SBR Compound

Free rubber-market dashboard at **sbrcompound.com**, sponsored by Carolina Recycle Partners.
It's a static website with no server or database. Scheduled GitHub jobs fetch public data, commit it to this repository, and GitHub Pages republishes the site.

```
config/dashboard.json   feeds, HTS codes, source links
marketdata/             fetchers for Census, World Bank, EIA, FRED, TCMB, RSS (shared with market-recycle)
pipelines/run.py        fetch jobs -> data/raw/
pipelines/build.py      data/raw/ -> site/data/*.json (what the site reads)
site/                   the website (served as-is; no build step)
tools/pages/            page bodies; run `python tools/render_pages.py` after editing
app/                    App Store wrapper (later phase)
```

## One-time setup

### 1. Accounts and free API keys
| Key | Where | Used for |
| --- | --- | --- |
| `CENSUS_API_KEY` | api.census.gov/data/key_signup.html | Trade data. Without it Census allows about 500 calls a day, and the first full load needs about 650. |
| `EIA_API_KEY` | eia.gov/opendata/register.php | Daily Brent and WTI prices |
| `FRED_API_KEY` | fredaccount.stlouisfed.org/apikeys | Rupee, real and baht exchange rates |

The lira (Turkish central bank), World Bank prices and news feeds need no key.

### 2. GitHub
1. Create a **private** repository named `sbrcompound` under the CRP GitHub account, and upload this folder. If you attach the repository to a Claude session, Claude can push it for you.
2. Under **Settings → Secrets and variables → Actions**, add the three keys above as repository secrets.
3. Under **Actions**, open *Update dashboard data* and choose **Run workflow** with `all`. The first run takes about 15 minutes.

### 3. Hosting: GitHub Pages (free)
The repository is public (it holds no keys and no private data). Under **Settings → Pages**, Source is **GitHub Actions**; `.github/workflows/pages.yml` publishes `site/` after every code push and every data update. Custom domain: `sbrcompound.com`, with **Enforce HTTPS** on.

### 4. DNS at Network Solutions
DNS stays at Network Solutions (nameservers unchanged). Records for sbrcompound.com:
| Type | Host | Value |
| --- | --- | --- |
| A | @ | 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 |
| CNAME | www | sbrcompound.github.io |

### 5. Email alerts (when ready)
Create a Buttondown account (free up to 100 subscribers). Put its username in `site/assets/app.js` → `newsletter.username`. Until then, the Alerts page says alerts are coming instead of collecting addresses.

## Running
- Data updates on its own: news every 3 hours, oil and currencies each weekday evening, trade and World Bank on Mondays.
- If a source fails, the workflow run fails and GitHub emails you. The site keeps the last good data.
- The monthly outlook text lives in `site/data/outlook.json`. It is drafted each month and published only after approval.

## If something breaks
- **World Bank 404:** the World Bank moved the workbook. Copy the new `CMO-Historical-Data-Monthly.xlsx` link from worldbank.org/en/research/commodity-markets into `config/dashboard.json`.
- **One news feed failing:** the other feeds still run, and `data/raw/status.json` names the broken one. Fix or remove it in `config/dashboard.json`.
- **Census trade data stuck on an old month:** normal for up to about five weeks after a month ends.

Sources: U.S. Census Bureau; World Bank Commodity Price Data; U.S. Energy Information Administration (EIA); Federal Reserve H.10 via FRED; Central Bank of the Republic of Türkiye; publisher RSS feeds (headlines and short excerpts only, linked to the publisher).
