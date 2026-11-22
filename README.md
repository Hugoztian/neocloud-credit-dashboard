# Neocloud Credit Dashboard

Static GitHub Pages site: a credit view of neoclouds and AI data-centre developers (CoreWeave, Nebius, Oracle OCI, IREN, Applied Digital, Cipher, TeraWulf, Hut 8, Core Scientific, Galaxy, Nscale, WhiteFiber, SpaceX/xAI compute, plus private Lambda, Crusoe, Fluidstack, Together AI and Vultr). Every figure is labelled Reported (SEC filing) / Mgmt / News / Calc and links to a dated source; filing wins over news; missing data is `n/a` with a reason.

Target URL: https://hugoztian.github.io/neocloud-credit-dashboard/

## Files
- `index.html`: the whole UI. Six tabs: Overview, Companies, Credit & stress, Capacity & supply, AI vs 2008 (with the systemic view), Sources & method. Institutional dark theme by default, light theme toggle (saved in `localStorage` key `ncd-theme`).
- `engine.js`: **the only place the credit math lives** (net debt, leverage, coverage, burn, runway, 24-month maturity cover, score). Used by the page (live recalculation), the build and the text export.
- `data.js`: **generated**. Do not edit by hand.
- `chart.umd.min.js`: vendored Chart.js (no CDN).
- `logo.png`, `favicon.png`: header seal and favicon.
- `tools/model.py`: engine inputs per company (USD m) with peer tier, collateral type, pro-forma items, market pricing, prepayment dependency, concentration, backstops, debt stack, and the pre-audit scores for the changelog.
- `tools/companies.py`: facts with labels, maturity ladders, counterparty inputs.
- `tools/sources.py`: every citation (title, URL, date, publisher).
- `tools/build_data.py`: merges the above, runs `engine.js` (via node) for headline and pro-forma scores, and holds What's new, Coming up, AI vs 2008, systemic tables, audit, discrepancies and gaps. Writes `data.js` with the SGT build time.
- `tools/totext.js`: writes a plain-text export for other AIs (`node tools/totext.js`).
- `.nojekyll`: serve files as-is. `preview_*.png`: local screenshots.

## Interactive features
- Global control bar (Overview, Companies, Credit & stress): **Basis** corporate (unrestricted cash, default) vs project-funded (adds restricted / ring-fenced cash); **Financing** quarter-end (default) vs pro-forma (adds all post-quarter raises symmetrically); **Debt** headline vs lease-adjusted; **EBITDA** reported vs recurring (Nebius ex $325.1m point-in-time revenue).
- Stress sliders: GPU revenue haircut 0 to −40%, refinancing shock +0 to +400bp, capex delay 0-6 months. Runway, coverage, 24M cover, leverage and score recalculate client-side.
- Score vs market-spread bubble chart (size = debt, colour = tier, click opens the drawer); interactive maturity wall (all / tier / single company, dashed liquidity line).
- Deep-dive drawer per company: live metrics, debt-stack donut, maturity ladder, counterparty concentration, backstop badges, prepayment dependency, pro-forma items, EDGAR links, all sourced facts.
- Compare mode: tick 2-3 scored companies on the Companies tab → radar of score components + metric diff.

## Definitions (headline)
- Net debt = debt principal − unrestricted cash (all companies). Liquidity = unrestricted cash + committed undrawn usable at quarter-end.
- Run-rate EBITDA = 4 × latest-quarter adjusted EBITDA (Oracle: TTM). Coverage = EBITDA / interest. Burn = (capex − operating cash flow) / 3. Runway = liquidity ÷ burn. 24M cover = liquidity ÷ principal due in the current and next year.
- Credit score (0-100, Calc): leverage 30 · coverage 25 · runway 20 · counterparty 15 · agency 5 · market 5.
  - Agency: A band+ 5, BBB 4, BB 2, B 1, unrated 0; split ratings take the lower; issue/project-level (or level not stated) −1.
  - Market: median bond spread over Treasuries ≤150bp 5, ≤250 4, ≤350 3, ≤500 2, ≤800 1, >800 0. Without priced bonds: highest-rate non-convertible borrowing − 4.83% 5-yr UST (Calc, lower confidence).

## Update the data
1. Check EDGAR for new 10-Q / 10-K / 6-K / 8-K filings (`https://data.sec.gov/submissions/CIK##########.json`, with a User-Agent header).
2. Edit `tools/model.py` (engine inputs, pro-forma items, market data) and `tools/companies.py` (facts text and source keys). A filing beats news.
3. Add any new citation to `tools/sources.py`.
4. Refresh `news` (rolling 7 days; last 48h highlighted automatically), `upcoming`, and the systemic tables in `tools/build_data.py`.
5. Run `python3 tools/build_data.py` (needs `node`). It fails if any figure cites a missing source key.
6. Optional: `node tools/totext.js` for the text export.
7. Preview with `python3 -m http.server 8080` in this folder, then open http://localhost:8080/.
8. Commit.

## Publish (only after Hugo's explicit OK)
1. Create the GitHub repo `hugoztian/neocloud-credit-dashboard` (public).
2. `git remote add origin https://github.com/hugoztian/neocloud-credit-dashboard.git && git push -u origin main`
3. Repo Settings → Pages → Source: *Deploy from a branch* → Branch `main`, folder `/ (root)` → Save.

Not investment advice.
