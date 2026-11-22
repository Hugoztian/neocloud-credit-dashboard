#!/usr/bin/env python3
"""Builds ../data.js from sources.py + companies.py + the editorial lists below.
Run:  python3 tools/build_data.py   (stamps the real build time in SGT, UTC+8)"""
import json, os, datetime as dt
from sources import S
from companies import PUB, PRIV

SGT = dt.timezone(dt.timedelta(hours=8))
now = dt.datetime.now(SGT)

def r1(x): return None if x is None else round(x, 1)

# ---------- credit math ----------
def metrics(c):
    i = c.get("inp")
    if not i: return dict(debt=(c.get("debt_override") or 0)/1000 or None, lev=None, cov=None, ecx=None, runway=None, burn=None, liq=None, nd=None, ebitda=None)
    e = i["ebitda_q"]*4 if i.get("ebitda_q") is not None else i["ttm_ebitda"]
    eq = i["ebitda_q"] if i.get("ebitda_q") is not None else e/4
    intr = i["ttm_int"] if i.get("ttm_int") else i["int_q"]*4
    nd = i["debt"] - i["cash_nd"]
    if "offbs" in i: nd_lev = nd + i["offbs"]
    else: nd_lev = nd
    lev = nd_lev/e if e > 0 else None
    cov = e/intr if intr else None
    ecx = (eq - i["capex_q"])/i["int_q"] if i.get("capex_q") is not None else None
    burn = (i["capex_q"] - i["ocf_q"])/3
    liq = i["cash_u"] + i["undrawn"]
    run = liq/burn if burn > 0 else None
    return dict(debt=i["debt"]/1000, lev=r1(lev), cov=None if cov is None else round(cov,2), ecx=r1(ecx), runway=r1(run),
                burn=round(burn), liq=round(liq), nd=round(nd), ebitda=round(e), cash_u=i["cash_u"], undrawn=i["undrawn"])

def pts_L(l, e):
    if l is None or e is None or e <= 0: return 0
    return 30 if l <= 3 else 22 if l <= 5 else 14 if l <= 8 else 7 if l <= 12 else 0
def pts_C(c): return 0 if c is None else 25 if c >= 5 else 18 if c >= 3 else 12 if c >= 2 else 6 if c >= 1 else 0
def pts_R(r): return 0 if r is None else 20 if r >= 24 else 14 if r >= 12 else 8 if r >= 6 else 3

companies = []
for c in PUB:
    m = metrics(c)
    d = {k: v for k, v in c.items() if k not in ("inp",)}
    d.update(m)
    if c.get("inp"):
        L, C, R = pts_L(m["lev"], m["ebitda"]), pts_C(m["cov"]), pts_R(m["runway"])
        d["score"] = L + C + R + c["Q"] + c["A"]
        d["scoreNote"] = f"Leverage {L} + Coverage {C} + Runway {R} + Counterparty {c['Q']} + Rating {c['A']} = {d['score']}"
    else:
        d["score"] = None; d["scoreNote"] = "n/a - " + c["scoreNA"]
    if c.get("debt_override"): d["debt"] = c["debt_override"]/1000
    companies.append(d)
for c in PRIV:
    d = dict(c); d.update(verified="Private - no filings", filing=None, debt=(c.get("debtNum") or 0)/1000 or None,
                      lev=None, cov=None, ecx=None, runway=None, score=None, scoreNote="n/a - private; figures are News/Mgmt, lower confidence",
                      potrev="n/a", capMW=None, capMWPlan=None, wall=None)
    companies.append(d)

# ---------- aggregates (Calc) ----------
core = [c for c in companies if c["id"] in ("crwv","nbis","iren","apld","cifr","wulf","glxy","corz","hut","nscl","wyfi")]
agg = dict(
  coreDebt=round(sum(c["debt"] for c in core), 1),
  coreBacklog=round(sum(c["backlog"] for c in core if c["backlog"]), 1),
  coreN=len(core),
  scored=len([c for c in companies if c["score"] is not None]),
  runwayU6=[c["name"] for c in companies if c["runway"] is not None and c["runway"] < 6],
  verifiedYes=[c["name"] for c in companies if str(c["verified"]).startswith("Yes")],
)
walls = {c["id"]: c["wall"] for c in companies if c.get("wall")}
dev = [0]*6
for k, w in walls.items():
    if k not in ("crwv", "nbis"):
        dev = [a+b for a, b in zip(dev, w)]
agg["wallSeries"] = [dict(name="CoreWeave", values=walls["crwv"]), dict(name="Nebius", values=walls["nbis"]),
                     dict(name="Developers (IREN, APLD, CIFR, WULF, HUT, CORZ, GLXY, WYFI)", values=[round(x,2) for x in dev])]

cost = [  # coupon/effective (Reported) or market yield (News)
 dict(label="CoreWeave 9.75% 2031 (market yield)", value=16.0, display="~16%", tag="News", src=["cnbcCds"]),
 dict(label="IREN GPU Financing 2.0 (effective)", value=10.70, display="10.70%", tag="Reported", src=["irenQ"]),
 dict(label="Galaxy Helios II 9.875% 2031", value=9.875, display="9.88%", tag="Reported", src=["glxyQ"]),
 dict(label="Sharon AI GPU facility B (comp)", value=9.95, display="9.95%", tag="Reported", src=["shaz"]),
 dict(label="Oracle 8.650% 2046 (new issue)", value=8.65, display="8.65%", tag="Reported", src=["orcl8k"]),
 dict(label="Saturn (xAI GPUs) Class A3 2033", value=8.259, display="8.26%", tag="News", src=["handoff"]),
 dict(label="WhiteFiber NC-1 loan (SOFR floor 2% + 6%)", value=8.0, display=">=8.00%", tag="Reported", src=["wyfi8k"]),
 dict(label="TeraWulf WULF Compute 2030", value=7.75, display="7.75%", tag="Reported", src=["wulfQ"]),
 dict(label="Core Scientific 2031 notes", value=7.75, display="7.75%", tag="Reported", src=["corzQ"]),
 dict(label="Nebius MUFG loan (effective)", value=7.6, display="7.60%", tag="Reported", src=["nbisFs"]),
 dict(label="Cipher Barber Lake 2030", value=7.125, display="7.13%", tag="Reported", src=["cifrQ"]),
 dict(label="IREN USPP (effective)", value=7.09, display="7.09%", tag="Reported", src=["irenQ"]),
 dict(label="Oracle 7.000% 2029 (new issue)", value=7.0, display="7.00%", tag="Reported", src=["orcl8k"]),
 dict(label="Applied Digital 7.00% 2031", value=7.0, display="7.00%", tag="Reported", src=["apldQ"]),
 dict(label="Hut 8 River Bend 2042", value=6.192, display="6.19%", tag="Reported", src=["hutQ"]),
 dict(label="SpaceX notes (weighted)", value=5.855, display="5.86%", tag="Reported", src=["spcxQ"]),
]

# ---------- What's new (rolling 7 days) ----------
news = [
 dict(date="2026-11-20", co="SPCX", tag="News", h="Apollo and Goldman price ~$44bn of senior and subordinated notes for SpaceX's Saturn GPU lease vehicle - 'largest GPU financing to date'",
      d="Oversubscribed and upsized; anchors BlackRock, Goldman Sachs Asset Management and KKR-advised accounts. Funds Nvidia Vera Rubin GPUs; lease schedules start on delivery in H1 2027. Off SpaceX's balance sheet.", src=["rtSaturn"]),
 dict(date="2026-11-20", co="ORCL", tag="Mgmt", h="Oracle says its OpenAI contract is fully funded, including vendor financing",
      d="Targets positive FCF in 2H FY28 and >$30bn FCF in FY29. Follows the 4 Nov $10bn notes (7.000%-8.650%) and 86.2m-share equity offering (8-K).", src=["orclStmt","orcl8k"]),
 dict(date="2026-11-20", co="CRWV", tag="News", h="CoreWeave falls 12% to $39.46, below its $40 IPO price; Huang Foundation's $350m CoreWeave compute commitment revives circular-financing concerns",
      d="New 52-week low $39.28. Foundation has spent $108.3m of the $350m. Seven Form 144 insider-sale notices filed on EDGAR the same day.", src=["saCrwv","yhHuang","crwv144"]),
 dict(date="2026-11-20", co="Counterparty", tag="News", h="Anthropic closes IPO: ~$93.5bn gross ($91.6bn to the company) plus a $26.0bn concurrent private placement",
      d="Key end-customer for Fluidstack (TeraWulf, Cipher, Hut 8 sites), Nscale (up to $44.6bn) and Lambda. Lambda's ~$34.9bn agreement remains terminable by either party; neither had given notice as of the 18 Nov prospectus.", src=["antIpo","jaLambda"]),
 dict(date="2026-11-18", co="CRWV / ORCL", tag="News", h="CoreWeave 5-yr CDS 1,100-1,200bp and 2031s near 16%; Oracle CDS above 300bp; first AI-CDS ETFs filed",
      d="Tuttle Capital and Defiance filed for ETFs that gain when CoreWeave/Oracle CDS widen. Co-founder Venturo disclosed buying $30m of CoreWeave 2031 unsecured bonds.", src=["cnbcCds","invCrwv"]),
 dict(date="2026-11-18", co="Nvidia", tag="News", h="Nvidia narrows its neocloud support: commitments cut to $32bn (from $36bn), effective only once financing is secured and capacity is deployed",
      d="Interim CEO Kress: guarantees start when projects are financed and would not survive construction delays. Morgan Stanley cut its deployment assumption to 4 GW from 5 GW.", src=["cnbcNvda","tcNvda"]),
 dict(date="2026-11-18", co="Macro", tag="News", h="Fed Governor Waller: a half-point hike may be needed at the December meeting",
      d="Higher floating rates would lift costs on SOFR-linked GPU and project loans (Nebius, IREN, Galaxy, WhiteFiber, Nscale).", src=["cnbcWaller"]),
 dict(date="2026-11-17", co="Fluidstack", tag="News", h="Situational Awareness pitches clients to co-invest in Fluidstack at a $40bn valuation (co-founder disputes the report)",
      d="Roughly double the $18bn Jane Street-led round of September.", src=["bbgFs","forbesFs"]),
 dict(date="2026-11-16", co="Comparable", tag="Reported", h="Sharon AI: $356m inaugural fixed-rate GPU-backed facility with Goldman and private credit funds (7.25% stepping to 9.95%; 9.95%)",
      d="Shows GPU-backed pricing for a small neocloud with IG-heavy contracts; >75% of expected secured debt tied to Nvidia's AI Compute Program.", src=["shaz"]),
]
earlier = [
 dict(date="2026-11-13", h="Nscale: debt jumped to $5.5bn at 30 Sep from $137m; Nvidia commits a further $1bn; more financing needed for 2027", src=["axiosNscl","nsclS1"]),
 dict(date="2026-11-12", h="Nebius 6-K: Q3 adj. EBITDA $465.8m includes $325.1m one-off revenue; FY26 revenue at low end of $3.0-3.4bn", src=["nbisFs","nbisPr"]),
 dict(date="2026-11-10", h="WhiteFiber signs $300m Morgan Stanley NC-1 term loan (SOFR+6.00%, 2% floor), unfunded; 10-Q filed", src=["wyfi8k","wyfiQ"]),
 dict(date="2026-11-10", h="CoreWeave Q3: backlog $132.5bn; Q4 interest guide $1.05-1.15bn; ~$9bn prepayments expected", src=["crwvPr"]),
 dict(date="2026-11-06", h="OpenAI closes ~$11bn first tranche at $1.25tn valuation; round could reach ~$20bn", src=["bbgOai"]),
 dict(date="2026-11-04", h="Oracle issues $10bn notes (7.000%-8.650%) and 86.2m shares; TeraWulf secures Google credit backstop", src=["orcl8k","wulfGoog"]),
]
upcoming = [
 dict(when="25 Nov 2026", what="BEA second estimate of Q3 GDP (denominator for the scale score)", kind="Macro", src=["beaQ3"]),
 dict(when="Rest of 2026", what="CoreWeave principal due: $2.4bn", kind="Maturity", src=["crwvQ"]),
 dict(when="Rest of 2026", what="Galaxy 2026 exchangeable notes (~$0.45bn) mature", kind="Maturity", src=["glxyQ"]),
 dict(when="By ~9 Dec 2026", what="WhiteFiber NC-1 $200m initial term-loan funding window (30 days from 9 Nov close; two 30-day extensions allowed)", kind="Deal closing", src=["wyfi8k"]),
 dict(when="8-9 Dec 2026", what="FOMC decision (Waller floated +50bp)", kind="Macro", src=["fomc","cnbcWaller"]),
 dict(when="~14 Dec 2026 (est., unconfirmed)", what="Oracle Q2 FY27 results", kind="Earnings", src=["orclDate"]),
 dict(when="Coming weeks", what="Nvidia Q3 FY27 10-Q (neocloud commitment detail); OpenAI round's remaining up to ~$9bn", kind="Filing / funding", src=["cnbcNvda","bbgOai"]),
 dict(when="Before YE 2026 (target)", what="Nscale IPO (price range not yet set)", kind="Deal closing", src=["axiosNscl","nsclS1"]),
 dict(when="Q4 2026", what="Cipher Barber Lake first delivery; TeraWulf CB-4; Applied Digital Polaris Forge 2 initial ops; Lambda $4bn round", kind="Delivery / funding", src=["cifrQ","wulfDeck","apldQ","tcLambda"]),
 dict(when="Early Jan 2027 (date n/a)", what="Applied Digital FQ2 FY27 results (quarter to 30 Nov)", kind="Earnings", src=["apldQ"]),
 dict(when="Jan-Feb 2027", what="IREN Microsoft capacity online; >$4bn ARR target", kind="Delivery", src=["irenPr"]),
 dict(when="H1 2027", what="Saturn GPU lease schedules start (SpaceX)", kind="Delivery", src=["rtSaturn"]),
 dict(when="Apr 2027", what="Hut 8 FalconX loan ($0.2bn, 7%) matures", kind="Maturity", src=["hutQ"]),
 dict(when="2027", what="CoreWeave maturities $11.0bn (largest single-year wall in the set)", kind="Maturity", src=["crwvQ"]),
]

# ---------- AI vs 2008 ----------
GDP07 = 14474.2; GDP26 = 33010.0; MORT07 = 11079.9; SUB07 = 1200.0
AI_CORE = 1200.0      # JPMorgan est. AI-company-issued debt (via Chicago Fed, Feb 2026)
AI_LEASE = 1200.0     # Moody's hyperscaler DC lease commitments by mid-2026 (via BIS Bulletin 140)
ratio = lambda a, g: round(100*a/g, 1)
scale = dict(
 rows=[
  dict(label="US home mortgages, end-2007", amt=MORT07, gdp=GDP07, pct=ratio(MORT07,GDP07), src=["z1","fredGdpa"], tag="Reported / Calc"),
  dict(label="Subprime mortgages outstanding, 2007", amt=SUB07, gdp=GDP07, pct=ratio(SUB07,GDP07), src=["gorton","fredGdpa"], tag="Reported (FCIC testimony) / Calc"),
  dict(label="AI-company-issued debt (JPMorgan est.)", amt=AI_CORE, gdp=GDP26, pct=ratio(AI_CORE,GDP26), src=["chiFed","fredQ3"], tag="News (bank estimate) / Calc"),
  dict(label="AI debt + hyperscaler DC lease commitments (Moody's)", amt=AI_CORE+AI_LEASE, gdp=GDP26, pct=ratio(AI_CORE+AI_LEASE,GDP26), src=["chiFed","bis140","fredQ3"], tag="News / Calc (upper bound; leases are not debt)"),
  dict(label="This dashboard's tracked neocloud & developer debt", amt=agg["coreDebt"], gdp=GDP26, pct=round(100*agg["coreDebt"]/GDP26,2), src=["fredQ3"], tag="Reported (sum) / Calc"),
 ])
sp = scale["rows"]
fA = min(100, round(100*sp[2]["pct"]/sp[1]["pct"])); fB = min(100, round(100*sp[3]["pct"]/sp[1]["pct"])); fC = min(100, round(100*sp[2]["pct"]/sp[0]["pct"]))
scale["factors"] = [
 dict(f="Core AI debt / GDP vs subprime / GDP", w=50, s=fA, why=f"{sp[2]['pct']}% vs {sp[1]['pct']}% of GDP"),
 dict(f="Broad AI debt + lease commitments / GDP vs subprime / GDP", w=25, s=fB, why=f"{sp[3]['pct']}% vs {sp[1]['pct']}% (upper bound)"),
 dict(f="Core AI debt / GDP vs all home mortgages / GDP", w=25, s=fC, why=f"{sp[2]['pct']}% vs {sp[0]['pct']}%"),
]
scale["score"] = round(sum(x["w"]*x["s"] for x in scale["factors"])/100)
scale["oneLine"] = (f"AI debt is ~{sp[2]['pct']}% of GDP (up to ~{sp[3]['pct']}% incl. lease commitments) vs subprime {sp[1]['pct']}% and all mortgages "
                    f"{sp[0]['pct']}% in 2007: comparable to the subprime slice, a fraction of the mortgage market.")

sim = [
 dict(f="Collateral that loses value vs longer debt and contract terms", w=15, s=70, side="Similar",
      why="GPUs: ECB cites a 1-3 year economic life vs 6-year accounting lives at hyperscalers; Nebius lengthened server lives to 5 years; contracts run ~5-6 years (Nscale ~5.7-yr weighted average; Saturn 5-yr lease). Houses lost value in 2007-09 but were not obsolete.", src=["ecb","nbisFs","nsclS1","rtSaturn"]),
 dict(f="Leverage and funding gap", w=15, s=55, side="Partly similar",
      why=f"Neocloud net leverage 4.6-16x; {len(agg['runwayU6'])} of {agg['scored']} scored names have under 6 months of runway on unrestricted cash. 2008 investment banks ran as high as 40:1 with overnight funding; hyperscalers are far less levered.", src=["fcic","crwvQ"]),
 dict(f="Circular financing (supplier funds customer funds supplier)", w=15, s=65, side="Similar",
      why="Nvidia: CoreWeave equity + $6.3bn capacity backstop, Nebius warrants, Nscale $2bn, $32bn contingent neocloud commitments, $118bn guarantees incl. up to $105bn residual-value support for OpenAI's Ohio campus; Huang Foundation buys CoreWeave compute; OpenAI and Anthropic are end customers behind Oracle, CoreWeave, Lambda, Nscale backlogs. ECB flags mutual commitments inflating reported demand.", src=["crwvNv","nbisFs","axiosNscl","cnbcNvda","nvda8k","cnbcNvdaQ3","yhHuang","ecb"]),
 dict(f="Off-balance-sheet vehicles", w=15, s=75, side="Similar",
      why="Meta Hyperion: $27.3bn A+ bonds, Meta 20% / Blue Owl 80%, not consolidated; Broadcom-Anthropic $63bn SPV (Broadcom residual support up to ~$43bn); SpaceX Saturn ~$44bn; Oracle $288bn of uncommenced leases off balance sheet; $75-100bn SPV bonds/ABS in 2026; ECB: big-tech off-balance-sheet commitments >$4tn. Echoes SIVs/conduits.", src=["spHyp","avgo8k","avgoPr","rtSaturn","orclQ","bis140","ecb"]),
 dict(f="Bond yields and CDS flashing stress", w=10, s=60, side="Similar",
      why="CoreWeave CDS 1,100-1,200bp, 2031s ~16%; Oracle CDS >300bp from <80; CDS ETFs filed. Comparable to early-2007 subprime ABX warnings; not yet a broad funding freeze.", src=["cnbcCds"]),
 dict(f="Who holds the risk", w=10, s=25, side="Different",
      why="Long-dated debt sits mostly with non-bank investors (bond funds, insurers, private credit with locked-up capital); large-bank AI C&I outstanding ~$150bn. 2008 risk sat in 40:1 banks funded overnight. Banks do lend to vehicles and to private-credit funds (BIS).", src=["bis140","chiFed","fcic"]),
 dict(f="Cash flow of the ultimate payer", w=10, s=30, side="Different",
      why="End payers are hyperscalers and well-funded labs (Anthropic raised ~$91.6bn in its IPO), not stretched households; but ECB notes most US hyperscalers turned FCF-negative in 2026, and OpenAI depends on new funding.", src=["antIpo","ecb","bbgOai"]),
 dict(f="Hard assets that keep value (power, land, buildings)", w=5, s=35, side="Different",
      why="Powered land, grid connections and shells (e.g. Hut 8, Applied Digital, Cipher project notes; Galaxy Helios) hold value better than GPUs; houses also had residual value but fell ~30%. Partial protection only.", src=["hutQ","apldQ","cifrQ"]),
 dict(f="Scale relative to the economy (from score 2)", w=5, s=scale["score"], side="Partly similar", why=scale["oneLine"], src=["z1","gorton","chiFed","fredQ3","fredGdpa"]),
]
simScore = round(sum(x["w"]*x["s"] for x in sim)/100)

telecom = [
 dict(k="Debt raised", t2000="Industry debt peaked at $306bn in 2000; capex >$444bn 1996-2001 (116 telecom companies)", ai="~$1.2tn AI-company debt (JPMorgan est.); top-5 hyperscaler bonds $222bn in 2026 to Sep; tracked neocloud/developer debt ${:.0f}bn".format(agg['coreDebt']), src=["lat","chiFed","bis140"]),
 dict(k="Defaults", t2000="2002 bond defaults $163bn worldwide, 56.4% telecom; telecom >52% of 2002 US high-yield defaulted dollars", ai="No defaults in the tracked set yet; CoreWeave CDS >1,000bp signals distress pricing", src=["oecd","altman","cnbcCds"]),
 dict(k="Utilisation", t2000="Long-haul fibre usage below 3% in Apr 2001 (from 15% in 1988); $90bn of fibre laid 1997-2001", ai="Capacity is largely pre-contracted (e.g. CoreWeave $132.5bn backlog, Nscale $105.8bn TCV) but contracts carry delivery conditions and termination rights (Lambda/Anthropic)", src=["dallas","crwvPr","nsclS1","jaLambda"]),
 dict(k="Recoveries", t2000="Communications defaults recovered ~16.6% on average in 2002", ai="n/a - no defaults yet; GPU loans rely on contract cash flows rather than resale value", src=["altman","shaz"]),
]
verdict = dict(
 text=("Closer to the 2000 telecom bust than to 2008 subprime. The structures rhyme with 2008 (off-balance-sheet vehicles, collateral that loses value, "
       "circular supplier financing, CDS flashing distress), but the risk sits mostly with non-bank, long-dated investors and equity holders rather than with "
       "overnight-funded banks, and the scale is similar to subprime alone, not to the whole mortgage market. Expect losses concentrated in neocloud equity, "
       "converts and high-yield/GPU debt (as telecom recoveries of ~17 cents showed), with spillover risk via banks' lending to vehicles and private credit funds."),
 watch=[
  dict(k="Bank holdings", v="Large-bank AI-adjacent C&I: ~$450bn commitments / ~$150bn outstanding (late 2025)", src=["chiFed"]),
  dict(k="Credit spreads", v="CoreWeave 5-yr CDS 1,100-1,200bp; 2031s ~16%; Oracle CDS >300bp (18 Nov 2026)", src=["cnbcCds"]),
  dict(k="OpenAI funding", v="~$11bn of up to ~$20bn closed at $1.25tn valuation (6 Nov 2026)", src=["bbgOai"]),
  dict(k="Refinancing / maturity walls", v="CoreWeave $11.0bn due 2027; set-wide wall clusters in 2030-31", src=["crwvQ"]),
  dict(k="Nvidia support", v="Neocloud commitments $32bn (down from $36bn), contingent on financing and deployment; total guarantees $118bn incl. $105bn OpenAI Ohio", src=["cnbcNvda","cnbcNvdaQ3"]),
  dict(k="Off-balance-sheet build-up", v=">$4tn big-tech commitments (Q2 2026); $75-100bn SPV bonds/ABS in 2026", src=["ecb","bis140"]),
 ])
macro = [
 dict(k="Morgan Stanley", v="~$2.9tn data-centre capex to 2028; $1.5tn external financing gap; ~$800bn from private credit", d="16 Jul 2025", src=["ms"]),
 dict(k="JPMorgan", v="~$1.5tn of AI/DC funding from IG bonds over five years; ~$1.2tn AI-company debt (cited by Chicago Fed)", d="10 Nov 2025 / Feb 2026", src=["jpmBbg","chiFed"]),
 dict(k="Moody's", v="At least $3tn data-centre investment through 2030; hyperscaler DC lease commitments $1.2tn by mid-2026 ($820bn not yet started)", d="12 Jan 2026 / Oct 2026", src=["moodysBbg","bis140"]),
 dict(k="BIS", v="Top-5 hyperscaler bonds $222bn in 2026 to Sep (>10% of long-term UST issuance); $75-100bn SPV bonds/ABS", d="27 Oct 2026", src=["bis140"]),
 dict(k="ECB", v="Big-tech off-balance-sheet commitments >$4tn (Q2 2026); most US hyperscalers FCF-negative in 2026", d="Nov 2026", src=["ecb"]),
]


claims = [
 dict(c="CoreWeave Q3 capex $14.5bn", st="Corrected", v="Cash capex $9.44bn (9M $23.56bn less H1 $14.12bn, 10-Q cash-flow statement). $14.5bn appears in neither the 10-Q nor the 8-K; accrual-basis additions are higher because $11.8bn of PP&E liabilities (incl. OEM-financed) were unpaid at 30 Sep", src=["crwvQ","crwvPr"]),
 dict(c="Nebius debt $14.19bn", st="Corrected (definition)", v="Net carrying amount $14,162.8m; principal $16,478.0m. Dashboard uses principal", src=["nbisFs"]),
 dict(c="IREN debt $8.9bn / cash $3.5bn", st="Corrected (definition)", v="$8.9bn is non-current debt only ($8,947m); total principal $10,041m (net $9,897m). $3.5bn is unrestricted cash ($3,522m); $5,778m incl. $2,256m restricted. Runway now uses $3.5bn", src=["irenQ"]),
 dict(c="Cipher debt $5.62bn", st="Corrected", v="Principal $6,016.3m; net carrying $5,447.2m. $5.62bn matches neither", src=["cifrQ"]),
 dict(c="Applied Digital debt n/a", st="Corrected", v="Principal $6,721.6m at 31 Aug 2026 (10-Q debt note and maturity table)", src=["apldQ"]),
 dict(c="WhiteFiber and Galaxy on Q2 data", st="Corrected", v="Both now on Q3 10-Qs (WhiteFiber filed 10 Nov 2026; Galaxy filed 9 Nov 2026)", src=["wyfiQ","glxyQ"]),
 dict(c="TeraWulf unrestricted cash $1.60bn excl. $753m restricted", st="Confirmed", v="$1,602.1m unrestricted; restricted $486.7m current + $266.5m non-current = $753.2m", src=["wulfQ"]),
 dict(c="Nvidia up to $105bn residual-value guarantee for OpenAI Ohio", st="Confirmed", v="8-K 17 Aug 2026: guaranties capped at $105bn for ~4.25 GW at SB Energy's PORTS campus; effective from lease commencement (~2028); OpenAI reimburses Nvidia", src=["nvda8k"]),
 dict(c="Nvidia $118bn total guarantees", st="Confirmed", v="$118bn at 25 Oct 2026 ($105bn Ohio + $9.5bn power/systems + $3.5bn neocloud land/power/shell); no payments made. Up from $108.5bn", src=["cnbcNvdaQ3","ttNvda"]),
 dict(c="Nvidia $32bn neocloud capacity commitments", st="Confirmed", v="$32bn at end-Q3 FY27 (from $36bn), effective only after financing, deployment and acceptance", src=["cnbcNvda","ttNvda"]),
 dict(c="Meta Hyperion / Beignet: $27bn debt on ~$30bn asset, Meta 20%", st="Confirmed", v="$27.3bn A+ notes due 2049; total committed $28.8bn (S&P) / ~$27bn development cost (Meta); Blue Owl funds 80%, Meta 20%; Meta residual value guarantee for 16 years", src=["spHyp","metaHyp","bis140"]),
 dict(c="Oracle $288bn uncommenced leases", st="Confirmed", v="10-Q (31 Aug 2026): $288bn of additional lease commitments, substantially all data centres, commencing Q2 FY27-FY29, 15-19 year terms, off balance sheet", src=["orclQ"]),
 dict(c="Broadcom $63bn SPV", st="Confirmed", v="$63bn SPV (BofA, Citi, Morgan Stanley first lien; Blackstone second lien) buys Broadcom XPU racks to lease to Anthropic; Broadcom residual value support, max ~$43bn (8-K)", src=["avgoPr","avgo8k"]),
 dict(c="Van Nieuwerburgh ~$1.4tn AI DC debt estimate", st="Corrected", v="The NBER paper estimates ~$9.0tn of US AI DC investment 2025-32 (3.2% of GDP a year), not debt. The '$1.4tn of debt issued to date' is an informal tally quoted at a Brookings event, not a paper estimate; not used in the scale score", src=["nber","brook"]),
 dict(c="Lambda ~$20bn Nvidia lease guarantees", st="Unverifiable", v="Only The Information (paywalled) reports it; it does not fit Nvidia's disclosed $118bn guarantee breakdown. Shown as unverified News on Lambda's card; excluded from calculations", src=["infoLambda","ttNvda"]),
 dict(c="AI debt 4.3% of GDP vs subprime 9.0%", st="Corrected", v=f"{sp[2]['pct']}% (JPMorgan ~$1.2tn ÷ Q3 2026 GDP $33.0tn) vs {sp[1]['pct']}% (subprime ~$1.2tn ÷ 2007 GDP $14.47tn). Using the $1.4tn informal tally would give ~4.2%; 9.0% would need ~$1.3tn of subprime", src=["chiFed","fredQ3","gorton","fredGdpa"]),
]

discrepancies = [
 dict(t="Runway definition changed", d="Runway now uses unrestricted cash + committed undrawn facilities. Hut 8 falls from 68 to ~11 months; Cipher to ~1.5 months; CoreWeave 4.6 → 3.7; Applied Digital 6.0 → 4.9; Core Scientific 10.3 → 5.1; IREN 16.7 → 12.5; TeraWulf 9.4 → 6.8.", s="Method", src=["hutQ","cifrQ","crwvQ"]),
 dict(t="Oracle debt after the 10-Q", d="Oracle issued $10bn notes and 86.2m shares on 4 Nov 2026 (8-K), after the 31 Aug 10-Q. Leverage and runway still use 10-Q balances.", s="Newer filing", src=["orcl8k"]),
 dict(t="Saturn notes", d="Handoff described tranche 'A3' as if it were a rating; A3 is the tranche class (maturing Apr 2033). Deal priced at ~$44bn on 20 Nov (Reuters).", s="Corrected", src=["rtSaturn","handoff"]),
 dict(t="IREN backlog vs RPO", d="Management's $20.3bn backlog vs $6.3bn RPO in XBRL; backlog includes lease contracts that RPO excludes.", s="Definition", src=["irenQ","irenPr"]),
 dict(t="Core Scientific capex", d="Q3 capex $985.1m in the results release (incl. land) vs $541m PP&E purchases in the 10-Q cash-flow statement. Filing figure used.", s="Filing used", src=["corzQ"]),
 dict(t="CoreWeave cash & backlog", d="$6.5bn cash on the call (incl. securities) vs $6.4bn incl. restricted / $4.1bn unrestricted in the 10-Q; $132.5bn backlog vs $132.3bn RPO.", s="Minor", src=["crwvQ","crwvPr"]),
 dict(t="Nebius EBITDA quality", d="Q3 adj. EBITDA includes $325.1m of non-recurring revenue; excluding it, leverage is ~16x rather than 4.9x.", s="Quality", src=["nbisFs"]),
 dict(t="Nebius maturity wall", d="Handoff placed the undrawn $3.5bn Citi facility in the 2027 maturity bucket and in liquidity. It is now liquidity only.", s="Corrected", src=["nbisFs"]),
 dict(t="WhiteFiber RPO drop", d="RPO fell to $729.0m at 30 Sep from $1,008.0m at 30 Jun (10-Q XBRL) even as the 10-year ~$865m Nscale order started billing; reason not explained in the extract reviewed.", s="Open", src=["wyfiQ"]),
 dict(t="Fluidstack funding", d="Fluidstack says it raised $830m in January at $7.5bn (Bloomberg); Dealroom reports a $750m round at $7.5bn. An unverified '$15bn project debt' figure is excluded.", s="Unverified", src=["bbgFs","drFs"]),
 dict(t="Private-company figures dropped", d="Handoff items without a dated source were removed: Lambda $926m TLB / ~$1bn May facility / JPMorgan loan; Crusoe ~$2.2bn corporate facilities, ~$2bn 2026 revenue, Abilene JV loans.", s="Removed", src=["handoff"]),
 dict(t="Nscale", d="Q3 figures are preliminary and unaudited (S-1/A); debt jumped from $137m (30 Jun) to $5.5bn (30 Sep).", s="Preliminary", src=["nsclS1"]),
 dict(t="Debt: principal vs carrying", d="Another AI's comparison used carrying or non-current amounts (Nebius $14.2bn, IREN $8.9bn, Cipher $5.6bn). The dashboard uses principal per filing debt notes: Nebius $16.48bn, IREN $10.04bn, Cipher $6.02bn, Applied Digital $6.72bn.", s="Definition", src=["nbisFs","irenQ","cifrQ","apldQ"]),
 dict(t="CoreWeave capex", d="Q3 cash capex is $9.44bn (10-Q cash flow); a $14.5bn figure circulating is not in the 10-Q or 8-K. Accrual-basis additions are higher ($11.8bn unpaid PP&E liabilities).", s="Filing used", src=["crwvQ"]),
 dict(t="Van Nieuwerburgh '$1.4tn debt'", d="The NBER paper's estimate is ~$9.0tn of investment, not debt; the $1.4tn debt figure is an informal tally from a Brookings event.", s="Corrected", src=["nber","brook"]),
 dict(t="Lambda '$20bn Nvidia guarantees'", d="Reported only by The Information; inconsistent with Nvidia's $118bn guarantee breakdown. Unverified, excluded from calculations.", s="Unverified", src=["infoLambda","ttNvda"]),
 dict(t="Oracle capex guide", d="FY27 capex of $90-95bn is from news, not the 10-Q.", s="News-only", src=["handoff"]),
]
gaps = ("Not disclosed: active MW for Nebius, IREN, Oracle, Cipher and Hut 8; Galaxy dollar backlog; Nscale financing costs, maturities, capex and interest; "
        "TeraWulf Google backstop size; total debt for Lambda, Crusoe, Fluidstack and Together AI; Oracle full maturity ladder after the Nov notes. "
        "Street estimates not collected (management guidance used). Agency ratings come from the earlier research pack (agency/news), not filings - "
        "original links not retained. Several named-contract sizes (CoreWeave-Meta/OpenAI, Nebius-Meta, Oracle-OpenAI) are News from the earlier pack.")

edgar = dict(checked=now.strftime("%d %b %Y %H:%M SGT"),
  result=("EDGAR submissions checked for all 13 SEC registrants. No 10-Q/10-K/20-F/6-K newer than the handoff. Newer filings incorporated: "
          "Oracle 8-K (4 Nov 2026, $10bn notes + equity), WhiteFiber 10-Q and 8-Ks (3 and 10 Nov 2026), CoreWeave Form 144s (20 Nov 2026). "
          "Reviewed, not material to credit: Oracle 8-K Item 5.07 (20 Nov), SpaceX 8-K Item 5.02 (6 Nov), Applied Digital 8-K Item 5.07 (6 Nov), Schedule 13G/13D and Form 4 filings."),
  src=["orcl8k","wyfiQ","wyfi8k","wyfi8kb","crwv144"])

out = dict(
  updated_iso=now.isoformat(timespec="seconds"), updated_sgt=now.strftime("%d %b %Y, %H:%M"), asof="22 Nov 2026",
  sources=S, companies=companies, agg=agg, cost=cost, news=news, earlier=earlier, upcoming=upcoming,
  scale=scale, sim=dict(factors=sim, score=simScore), telecom=telecom, verdict=verdict, macro=macro,
  discrepancies=discrepancies, claims=claims, gaps=gaps, edgar=edgar,
)
# integrity check: every src key exists
def keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "src" and isinstance(v, list):
                for x in v: yield x
            elif k == "filing" and isinstance(v, dict): yield v["src"]
            else: yield from keys(v)
    elif isinstance(o, list):
        for v in o:
            if isinstance(v, tuple) and len(v) == 3:
                for x in v[2]: yield x
            else: yield from keys(v)
missing = sorted({k for k in keys(out) if k not in S})
assert not missing, missing
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "..", "data.js"), "w") as f:
    f.write("// Neocloud Credit Dashboard data - generated by tools/build_data.py. Do not edit by hand.\n")
    f.write("window.NCD = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n")
print("built", out["updated_sgt"], "SGT | sim", simScore, "| scale", scale["score"], "| coreDebt", agg["coreDebt"])
for c in companies:
    print(f"{c['name']:22} score {c['score']} lev {c['lev']} cov {c['cov']} ecx {c['ecx']} run {c['runway']} debt {c['debt']}")
print(scale["rows"]); print([ (x['f'][:25],x['s']) for x in scale['factors']])
