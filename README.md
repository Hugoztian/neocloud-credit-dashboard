# Neocloud Credit Dashboard

Static GitHub Pages site: a credit view of neoclouds and AI data-centre developers (CoreWeave, Nebius, Oracle OCI, IREN, Applied Digital, Cipher, TeraWulf, Hut 8, Core Scientific, Galaxy, Nscale, WhiteFiber, SpaceX/xAI compute, plus private Lambda, Crusoe, Fluidstack, Together AI and Vultr).

Target URL: https://hugoztian.github.io/neocloud-credit-dashboard/

## Files
- `index.html`: the whole UI (6 tabs: Overview, Companies, Credit math, Capacity & supply, AI vs 2008, Sources & method). Light/dark toggle.
- `data.js`: **generated**. Do not edit by hand.
- `chart.umd.min.js`: vendored Chart.js (no CDN needed).
- `tools/sources.py`: every citation (`title`, `url`, `date`, `publisher`). Each figure on the site points to one or more keys here.
- `tools/companies.py`: per-company inputs (USD m), facts with Reported / Mgmt / News / Calc labels, maturity ladders, and counterparty/rating score inputs.
- `tools/build_data.py`: credit math, scores, What's new, Coming up, the AI vs 2008 comparison and scores, discrepancies, claims check. Writes `data.js` and stamps the real build time in SGT (UTC+8).
- `.nojekyll`: serve files as-is.
- `preview_*.png`: local preview screenshots.

## Update the data
1. Check EDGAR for new 10-Q / 10-K / 20-F / 6-K / 8-K filings (`https://data.sec.gov/submissions/CIK##########.json`, with a User-Agent header).
2. Edit `tools/companies.py`: `inp` (debt principal, `cash_nd` = cash incl. restricted for net debt, `cash_u` = **unrestricted** cash for runway, committed `undrawn`, quarterly `ebitda_q`, `int_q`, `capex_q`, `ocf_q`), the facts text, and the source keys. A filing beats news. Use `n/a - reason` instead of guessing.
3. Add any new citation to `tools/sources.py` (title, URL, date).
4. Refresh `news` (rolling 7 days; anything within 48h is highlighted automatically) and `upcoming` in `tools/build_data.py`.
5. Run `python3 tools/build_data.py`. It fails if any figure cites a missing source key.
6. Preview with `python3 -m http.server 8080` in this folder, then open http://localhost:8080/ (opening via file:// also works).
7. Commit.

## Definitions
- Run-rate EBITDA = 4 × latest-quarter adjusted EBITDA (Oracle: TTM operating income + depreciation).
- Net debt = debt principal − cash incl. restricted.
- Cash runway = (unrestricted cash + committed undrawn facilities) ÷ ((capex − operating cash flow) / 3). Restricted cash is excluded.
- Credit score (0-100, Calc): leverage 30, coverage 25, runway 20, counterparty 15, rating 10.

## Publish (only after Hugo's explicit OK)
1. Create the GitHub repo `hugoztian/neocloud-credit-dashboard` (public).
2. `git remote add origin https://github.com/hugoztian/neocloud-credit-dashboard.git && git push -u origin main`
3. Repo Settings → Pages → Source: *Deploy from a branch* → Branch `main`, folder `/ (root)` → Save.
4. The site goes live at https://hugoztian.github.io/neocloud-credit-dashboard/ within a minute or two.

Not investment advice.
