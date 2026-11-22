#!/usr/bin/env python3
"""Builds ../data.js from sources.py + companies.py + the editorial lists below.
Run:  python3 tools/build_data.py   (stamps the real build time in SGT, UTC+8)"""
import json, os, datetime as dt
from sources import S
from companies import PUB, PRIV

SGT = dt.timezone(dt.timedelta(hours=8))
now = dt.datetime.now(SGT)

def r1(x): return None if x is None else round(x, 1)
from model import M, PRIV_TIER, OLD, UST5
import subprocess

# ---------- credit math: one engine (../engine.js) for browser, export and this build ----------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def run_engine(cos, settings_list):
    js = ("const E=require(%r);const cos=JSON.parse(process.argv[1]);const ss=JSON.parse(process.argv[2]);"
          "console.log(JSON.stringify(ss.map(st=>Object.fromEntries(cos.map(c=>[c.id,E.calc(c,st)])))))") % os.path.join(ROOT, "engine.js")
    out = subprocess.run(["node", "-e", js, json.dumps(cos), json.dumps(settings_list)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)

companies = []
for c in PUB:
    d = {k: v for k, v in c.items() if k not in ("inp", "A")}
    m = M.get(c["id"], {})
    d.update({k: v for k, v in m.items()})
    if d.get("inp"): d["inp"] = dict(d["inp"])
    d["debt"] = (c["debt_override"] if c.get("debt_override") else (c["inp"]["debt"] if c.get("inp") else 0))/1000 or None
    if not d.get("inp"): d["scoreNote"] = "n/a - " + c["scoreNA"]
    d["oldScore"] = OLD.get(c["id"])
    companies.append(d)
for c in PRIV:
    t = PRIV_TIER.get(c["id"], ("GPU Neocloud", "Depreciating silicon"))
    d = dict(c); d.update(verified="Private - no filings", filing=None, debt=(c.get("debtNum") or 0)/1000 or None, inp=None, tier=t[0], coll=t[1],
                      scoreNote="n/a - private; figures are News/Mgmt, lower confidence", potrev="n/a", capMW=None, capMWPlan=None, wall=None)
    companies.append(d)

scored = [c for c in companies if c.get("inp")]
BASE, PF, PROJ, LEASE = run_engine(scored, [{}, {"fin": "pf"}, {"basis": "proj"}, {"debt": "lease"}])
for c in scored:
    b = BASE[c["id"]]
    c["base"] = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in b.items()}
    c["score"] = b["score"]; c["scoreNote"] = b["note"]
    c["scorePF"] = PF[c["id"]]["score"]

# ---------- aggregates (Calc, strict quarter-end, corporate basis) ----------
core = [c for c in companies if c["id"] in ("crwv","nbis","iren","apld","cifr","wulf","glxy","corz","hut","nscl","wyfi")]
agg = dict(
  coreDebt=round(sum(c["debt"] or 0 for c in core), 1),
  coreBacklog=round(sum(c["backlog"] for c in core if c["backlog"]), 1),
  coreN=len(core),
  scored=len(scored),
  runwayU6=[c["name"] for c in scored if BASE[c["id"]]["run"] is not None and BASE[c["id"]]["run"] < 6],
  verifiedYes=[c["name"] for c in companies if str(c["verified"]).startswith("Yes")],
  ust5=UST5,
)
levs = sorted(BASE[k]["lev"] for k in ("crwv","nbis","iren","apld","corz","hut") if BASE[k]["lev"])
agg["levRange"] = [round(levs[0], 1), round(levs[-1], 1)]

# ---------- score changelog (old 10-pt rating bucket, mixed cash basis -> new A5+M5, unrestricted cash, strict quarter-end) ----------
WHY = {
 "crwv": "Rating bucket 3 → agency 1 (B band) + market 0 (median spread 1,051bp); undrawn $5.7bn Reported (was ~$5bn Mgmt)",
 "nbis": "Rating 0 → agency 0 + market 3 (fallback: MUFG 7.60% − UST5); Citi $3.5bn moved to pro-forma; restricted cash excluded (already)",
 "orcl": "Rating 8 → agency 4 (BBB band) + market 3 (318bp); Nov raises only on pro-forma",
 "iren": "Rating 0 → agency 0 + market 1 (fallback: GPU Financing 3.0 10.38%)",
 "apld": "Counterparty 15 → 10 (CoreWeave anchors Polaris Forge 1); rating 3 → agency 1 + market 2 (352bp)",
 "cifr": "Rating 3 → agency 1 (project notes) + market 4 (239bp); restricted $2.2bn excluded in headline; Oct converts pro-forma only",
 "wulf": "Rating 3 → agency 1 (project notes) + market 4 (210bp); $400m revolver → ~$1m usable at quarter-end (cap $75m less $74m LCs)",
 "hut":  "Rating 10 → agency 3 (BBB-/Baa2 on project notes: 4 − 1 for project level) + market 4 (fallback FalconX 7%); restricted cash and investments ($6.39bn) no longer netted",
 "corz": "Rating 3 → agency 1 + market 2 (437bp)",
 "wyfi": "Rating 0 → agency 0 + market 1 (fallback: NC-1 margin SOFR + 6.00% ≈ 600bp); $70m Oct DDTL advance only on pro-forma",
 "spcx": "Rating 9 → agency 4 + market 4 (fallback: top coupon 6.65% − UST5 4.83% = 182bp); xAI 12.5% notes repaid (Mar 2026)",
}
changelog = []
for c in scored:
    changelog.append(dict(id=c["id"], name=c["name"], old=OLD.get(c["id"]), new=c["score"], pf=c["scorePF"],
                          delta=None if OLD.get(c["id"]) is None else c["score"] - OLD[c["id"]], why=WHY.get(c["id"], ""), note=c["scoreNote"]))

cost = [  # coupon/effective (Reported) or market yield (News)
 dict(label="CoreWeave 9.75% 2031 (market yield, 19 Nov)", value=15.64, display="15.64%", tag="News", src=["aiTracker"]),
 dict(label="Galaxy Helios 2031 (market yield, 19 Nov)", value=12.24, display="12.24%", tag="News", src=["aiTracker"]),
 dict(label="Core Scientific 2031 (market yield, 19 Nov)", value=9.21, display="9.21%", tag="News", src=["aiTracker"]),
 dict(label="Oracle 6.85% 2066 (market yield, 19 Nov)", value=8.87, display="8.87%", tag="News", src=["aiTracker"]),
 dict(label="Applied Digital 2031 (market yield, 19 Nov)", value=8.85, display="8.85%", tag="News", src=["aiTracker"]),
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
      d="Oversubscribed and upsized; anchors BlackRock, Goldman Sachs Asset Management and KKR-advised accounts. Funds Nvidia Vera Rubin GPUs; lease schedules start on delivery in H1 2027. SpaceX's own 8-K (26 Oct) sizes the Apollo master finance lease at ~$40bn; a finance lease comes on balance sheet at commencement.", src=["rtSaturn","spcx8kLease"]),
 dict(date="2026-11-20", co="ORCL", tag="Mgmt", h="Oracle says its OpenAI contract is fully funded, including vendor financing",
      d="Targets positive FCF in 2H FY28 and >$30bn FCF in FY29. Follows the 4 Nov $10bn notes (7.000%-8.650%) and 86.2m-share equity offering (8-K).", src=["orclStmt","orcl8k"]),
 dict(date="2026-11-20", co="CRWV", tag="News", h="CoreWeave falls 12% to $39.46, below its $40 IPO price; Huang Foundation's $350m CoreWeave compute commitment revives circular-financing concerns",
      d="New 52-week low $39.28. Foundation has spent $108.3m of the $350m. Seven Form 144 insider-sale notices filed on EDGAR the same day.", src=["saCrwv","yhHuang","crwv144"]),
 dict(date="2026-11-20", co="Counterparty", tag="News", h="Anthropic closes IPO: ~$93.5bn gross ($91.6bn to the company) plus a $26.0bn concurrent private placement",
      d="Key end-customer for Fluidstack (TeraWulf, Cipher, Hut 8 sites), Nscale (up to $44.6bn) and Lambda. Lambda's ~$34.9bn agreement remains terminable by either party; neither had given notice as of the 18 Nov prospectus.", src=["antIpo","jaLambda"]),
 dict(date="2026-11-18", co="CRWV / ORCL", tag="News", h="CoreWeave 5-yr CDS 1,100-1,200bp and 2031s near 16%; Oracle CDS above 300bp; first AI-CDS ETFs filed",
      d="Tuttle Capital and Defiance filed for ETFs that gain when CoreWeave/Oracle CDS widen. Co-founder Venturo disclosed buying $30m of CoreWeave 2031 unsecured bonds.", src=["cnbcCds","invCrwv"]),
 dict(date="2026-11-17", co="Grid", tag="News", h="Utility Dive: ~191 GW of planned data-centre capacity faces new risk as the build-out slows (Orennia)",
      d="Utilities plan ~$1.3tn of capex in 2026-30 (S&P RRA); Rystad's risked view sees pauses delaying ~1-3 GW, more than 10 GW if sustained.", src=["udive","spUtil","rystad"]),
 dict(date="2026-11-16", co="Macro", tag="News", h="Fed Governor Barr: AI investment is increasingly debt-funded and it is hard to know where the risk sits",
      d="Hyperscalers and GPU makers have made >$100bn of equity investments in model labs and cloud start-ups that are also their customers. Follows the 13 Nov Financial Stability Report: >$3tn of off-balance-sheet obligations at seven firms.", src=["barr","fedFsr"]),
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
      why=f"Net leverage ~4.8x at CoreWeave and Nebius (Nebius ~16x on recurring EBITDA), >14x at Applied Digital, IREN and Hut 8; {len(agg['runwayU6'])} of {agg['scored']} scored names have under 6 months of runway on unrestricted cash. 2008 investment banks ran as high as 40:1 with overnight funding; hyperscalers are far less levered.", src=["fcic","crwvQ"]),
 dict(f="Circular financing (supplier funds customer funds supplier)", w=15, s=65, side="Similar",
      why="Nvidia: CoreWeave equity + $6.3bn capacity backstop, Nebius warrants, Nscale $2bn, $32bn contingent neocloud commitments, $118bn guarantees incl. up to $105bn residual-value support for OpenAI's Ohio campus; Huang Foundation buys CoreWeave compute; OpenAI and Anthropic are end customers behind Oracle, CoreWeave, Lambda, Nscale backlogs. ECB flags mutual commitments inflating reported demand.", src=["crwvNv","nbisFs","axiosNscl","cnbcNvda","nvda8k","cnbcNvdaQ3","yhHuang","ecb"]),
 dict(f="Off-balance-sheet vehicles", w=15, s=75, side="Similar",
      why="Meta Hyperion: $27.3bn A+ bonds, Meta 20% / Blue Owl 80%, not consolidated; Broadcom-Anthropic $63bn SPV (Broadcom residual support up to ~$43bn); SpaceX ~$40bn GPU finance lease (8-K; on balance sheet only from commencement in 2027); Oracle $288bn of uncommenced leases off balance sheet; Fed: >$3tn of off-balance-sheet obligations at seven firms; $75-100bn SPV bonds/ABS in 2026; ECB: big-tech off-balance-sheet commitments >$4tn. Echoes SIVs/conduits.", src=["spHyp","avgo8k","avgoPr","spcx8kLease","orclQ","fedFsr","bis140","ecb"]),
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
  dict(k="Off-balance-sheet build-up", v="Fed: >$3tn at seven firms (>$1tn uncommenced leases + >$2tn take-or-pay and residual-value guarantees, undiscounted); ECB: >$4tn big-tech commitments (Q2 2026); $75-100bn SPV bonds/ABS in 2026", src=["fedFsr","ecb","bis140"]),
 ])
macro = [
 dict(k="Morgan Stanley", v="~$2.9tn data-centre capex to 2028; $1.5tn external financing gap; ~$800bn from private credit", d="16 Jul 2025", src=["ms"]),
 dict(k="JPMorgan", v="~$1.5tn of AI/DC funding from IG bonds over five years; ~$1.2tn AI-company debt (cited by Chicago Fed)", d="10 Nov 2025 / Feb 2026", src=["jpmBbg","chiFed"]),
 dict(k="Moody's", v="At least $3tn data-centre investment through 2030; hyperscaler DC lease commitments $1.2tn by mid-2026 ($820bn not yet started)", d="12 Jan 2026 / Oct 2026", src=["moodysBbg","bis140"]),
 dict(k="BIS", v="Top-5 hyperscaler bonds $222bn in 2026 to Sep (>10% of long-term UST issuance); $75-100bn SPV bonds/ABS", d="27 Oct 2026", src=["bis140"]),
 dict(k="Federal Reserve", v="Advanced-computing firms issued >$680bn of debt in 2026 to October (~31% of nonfinancial IG issuance); public debt outstanding >$1.1tn; off-balance-sheet obligations >$3tn", d="13 Nov 2026", src=["fedFsr"]),
 dict(k="Goldman Sachs", v="Hyperscaler gross debt issuance ~$420bn in 2027, 65-75% expected in USD IG", d="22 Sep 2026", src=["rtGs"]),
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


# ---------- second-AI audit (22 Nov 2026): every number treated as a claim ----------
audit = [
 dict(g="Data / formula", c="Net debt mixes cash bases; Hut 8 net debt $1,175m should be ~$7,569.5m", st="Confirmed", v="Old build netted Hut 8's $6.39bn restricted cash and investments. All companies now use unrestricted cash; Hut 8 net debt = $7,726.4m − $156.9m = $7,569.5m · Calc", src=["hutQ"]),
 dict(g="Data / formula", c="Post-quarter financing applied asymmetrically (Nebius, TeraWulf in; Oracle, Cipher out)", st="Confirmed", v="Headline is now strict quarter-end; a pro-forma toggle adds all raises. Nebius Citi $3.5bn (6-K 22 Oct) and Cipher $850m 0% 2032 converts (16 Oct, 10-Q subsequent events) confirmed", src=["nbis6kCiti","cifrQ"]),
 dict(g="Data / formula", c="TeraWulf $400m revolver adds liquidity", st="Corrected", v="At 30 Sep borrowings + LCs were capped at $75m before first lease commencement with $74.0m of LCs out (~$1m usable). The Oct amendment raised commitments to $400m but the pre-commencement cap only to $150m (~$76m usable, pro-forma)", src=["wulfQ","wulf8kRev"]),
 dict(g="Data / formula", c="Oracle Nov 2026 '$10B notes/equity'", st="Corrected", v="$10.0bn of notes (7.000-8.650%) and, separately, $10.0bn of common stock (86.2m shares): $20bn gross. Pro-forma adds +$20bn cash, +$10bn debt", src=["orcl8k"]),
 dict(g="Data / formula", c="Nebius $980.8m revenue includes $325.1m one-off; run-rate EBITDA $1,863m overstated", st="Confirmed", v="Filing: $325.1m 'revenue from strategic partnerships', recognised at a point in time. Recurring view: ($465.8m − $325.1m) × 4 = $563m; leverage ~16x vs 4.9x · Calc", src=["nbisFs"]),
 dict(g="Data / formula", c="Applied Digital debt shown as $6.7216000000000005bn", st="Confirmed (bug)", v="Floating-point display bug; all numbers now go through one formatter ($6.72bn)", src=["apldQ"]),
 dict(g="Rubric", c="Oracle: $43.8bn on-balance-sheet leases and $288bn uncommenced", st="Confirmed", v="Operating lease liabilities $34,621m + finance $9,185m = $43,806m; $288bn of leases not yet commenced (10-Q). Lease-adjusted view added", src=["orclQ"]),
 dict(g="Rubric", c="S&P sees Oracle lease-adjusted leverage in the mid-4x range", st="Confirmed", v="S&P (Jul 2026): mid-4x in FY27 after adding $260bn of leases and $13bn of power obligations; downgrade risk if >4.5x · News", src=["ppcSP"]),
 dict(g="Rubric", c="Oracle BBB-/Baa2 negative; CDS >300bp", st="Confirmed", v="Moody's affirmed Baa2, outlook negative, 2 Nov 2026; S&P BBB-; CDS above 300bp (18 Nov) · News", src=["moodysOrcl","ppcSP","cnbcCds"]),
 dict(g="Rubric", c="Applied Digital counterparty 15/15 despite CoreWeave anchoring Polaris Forge 1 (400 MW)", st="Confirmed", v="CoreWeave leases 400 MW of ~1.41 GW at Polaris Forge 1 (10-Q). Counterparty cut to 10/15", src=["apldQ"]),
 dict(g="Rubric", c="Hut 8 gets 10/10 rating on project notes with 0.31x coverage; CoreWeave 3/10 at ~16% yields and >1,100bp CDS", st="Confirmed", v="Hut 8 BBB-/Baa2 notes are project-level; corporate EBITDA/interest 0.31x · Calc. CoreWeave 2031s 15.64% (19 Nov) and CDS 1,100-1,200bp · News. Bucket now 5 agency + 5 market", src=["hutQ","aiTracker","cnbcCds"]),
 dict(g="Addition", c="24M maturity coverage: CoreWeave 0.68x vs TeraWulf 9.0x", st="Corrected", v="CoreWeave 0.73x using the Reported $5.7bn undrawn ((4,122 + 5,700) ÷ 13,400); TeraWulf 7.2x strict ((1,602 + 1) ÷ 224), 7.5x pro-forma; 9.0x only if the full $400m revolver were usable · Calc", src=["crwvQ","wulfQ","wulf8kRev"]),
 dict(g="Addition", c="Cipher 1.5 months corporate runway vs $2.2bn ring-fenced project cash", st="Confirmed", v="Restricted cash $2,196.6m (10-Q). Runway ~1.5 months corporate vs ~5.4 project-funded · Calc", src=["cifrQ"]),
 dict(g="Addition", c="CoreWeave ~$9bn prepayments vs ~$11.8bn unpaid PP&E", st="Confirmed", v="~$9bn prepayments/deposits expected in the next 3 months · Mgmt (call 10 Nov); $11.8bn unpaid PP&E liabilities · Reported", src=["foolCrwv","crwvQ"]),
 dict(g="Addition", c="Nebius prepayments ~$10bn (2026) and $17-20bn (2027)", st="Confirmed", v="Q3 call · Mgmt", src=["foolNbis"]),
 dict(g="Addition", c="CoreWeave undrawn liquidity ~$5bn", st="Corrected", v="$5.7bn undrawn under the revolver, DDTL 4.0 and DDTL 5.5 · Reported (10-Q); '~$5bn' was the call's DDTL-only figure", src=["crwvQ","foolCrwv"]),
 dict(g="Systemic", c="Fed: >$3tn off-balance-sheet AI obligations", st="Confirmed", v="Fed FSR (13 Nov 2026) Box 2.2: >$1tn not-yet-commenced leases + >$2tn take-or-pay and residual-value guarantees at seven firms; undiscounted", src=["fedFsr"]),
 dict(g="Systemic", c="Meta Hyperion $27bn at ~90% LTV", st="Confirmed", v="$27.3bn of notes (S&P) vs ~$30bn asset → ~90% (Van Nieuwerburgh, Brookings); vs S&P's $28.8bn committed cost ~95% · Calc", src=["spHyp","brook"]),
 dict(g="Systemic", c="Broadcom $63bn SPV; Nvidia $32bn + $105bn+ backstops", st="Confirmed", v="Broadcom 8-K: $63bn SPV, residual support up to ~$43bn. Nvidia: $32bn neocloud commitments; $118bn guarantees incl. up to $105bn for OpenAI Ohio", src=["avgo8k","avgoPr","cnbcNvda","cnbcNvdaQ3","nvda8k"]),
 dict(g="Systemic", c="~$1.4tn AI debt stack, ~50% banks / ~50% private credit", st="Unverifiable", v="An informal tally quoted at a Brookings event (8 Oct 2026), not a measured estimate. The Fed instead reports >$1.1tn of public advanced-computing debt held mainly by mutual funds, pensions and insurers; large-bank AI C&I ~$150bn outstanding (Chicago Fed). Not used", src=["brook","fedFsr","chiFed"]),
 dict(g="Systemic", c="$50-59bn of AI ABS/CMBS", st="Unverifiable", v="Not found in a readable dated source (the CREFC deck has no text layer). BIS puts SPV-linked bonds/ABS at $75-100bn in 2026. Not used", src=["bis140"]),
 dict(g="Systemic", c="Untraceable holders / opacity gap", st="Confirmed (qualitative)", v="Fed: private-credit and SPV structures make the debt hard to measure; Barr (16 Nov): hard to know where the risk resides. No number to verify", src=["fedFsr","barr"]),
 dict(g="Macro", c="$420bn hyperscaler issuance in 2027", st="Confirmed", v="Goldman Sachs forecast of gross hyperscaler debt issuance, 65-75% in USD IG (Reuters, 22 Sep 2026) · News", src=["rtGs"]),
 dict(g="Macro", c="US utility capex ~$1.3tn in 2026-30", st="Confirmed", v="S&P RRA: $1.295tn across 46 utilities (23 Apr 2026) · News", src=["spUtil"]),
 dict(g="Macro", c="191 GW of data-centre capacity at siting risk after the midterms", st="Confirmed", v="Orennia via Utility Dive (17 Nov 2026): ~191 GW of planned capacity faces new risk. Rystad's risked view: delays of ~1-3 GW (>10 GW if sustained) · News", src=["udive","rystad"]),
 dict(g="Macro", c="GAAP depreciation 5-6 years vs 3-4 year economic GPU life", st="Corrected", v="Nebius extended server lives from 4 to 5 years in 2026 · Reported; ECB cites 6-year accounting lives vs 1-3 year economic life · News. The '3-4 year' figure has no dated source", src=["nbisFs","ecb"]),
 dict(g="Prior pack", c="SpaceX xAI 12.5% notes outstanding", st="Corrected", v="Repaid 5 Mar 2026 (10-Q)", src=["spcxQ"]),
 dict(g="Prior pack", c="Saturn ~$44bn", st="Corrected (filing wins)", v="SpaceX 8-K (26 Oct): ~$40bn Apollo master finance lease; $44bn is Reuters' 20 Nov deal size · News", src=["spcx8kLease","rtSaturn"]),
]

# ---------- systemic (inside the AI vs 2008 tab) ----------
obs = [
 dict(k="Seven large AI firms (Fed)", v=">$3tn", d=">$1tn not-yet-commenced leases + >$2tn take-or-pay and residual-value guarantees; undiscounted", tag="News (Fed FSR)", src=["fedFsr"]),
 dict(k="Oracle uncommenced leases", v="$288bn", d="Data centres; commence Q2 FY27-FY29; 15-19 year terms", tag="Reported", src=["orclQ"]),
 dict(k="Nvidia guarantees", v="$118bn", d="Incl. up to $105bn residual-value guaranties for OpenAI Ohio; plus $32bn contingent neocloud capacity commitments", tag="Reported / News", src=["nvda8k","cnbcNvdaQ3","cnbcNvda"]),
 dict(k="Broadcom-Anthropic SPV", v="$63bn", d="Broadcom residual-value support up to ~$43bn", tag="Reported", src=["avgo8k","avgoPr"]),
 dict(k="SpaceX GPU finance lease", v="~$40bn", d="Apollo-managed; commences H1 2027", tag="Reported", src=["spcx8kLease"]),
 dict(k="Meta Hyperion (Beignet)", v="$27.3bn", d="Notes on a ~$30bn asset (~90% LTV · Calc); Meta 20% / Blue Owl 80%; 16-year residual-value guarantee", tag="News", src=["spHyp","metaHyp","brook"]),
]
holders = [
 dict(k="Public debt of advanced-computing firms", v=">$1.1tn outstanding; >$680bn issued in 2026 to Oct", d="Held mainly by mutual funds, pensions and insurers (Fed)", tag="News (Fed FSR)", src=["fedFsr"]),
 dict(k="Large-bank AI-adjacent C&I", v="~$450bn commitments / ~$150bn drawn", d="Late 2025", tag="News (Chicago Fed)", src=["chiFed"]),
 dict(k="SPV bonds / ABS", v="$75-100bn in 2026", d="BIS Bulletin 140", tag="News", src=["bis140"]),
 dict(k="Private credit (forecast)", v="~$800bn of a $1.5tn gap to 2028", d="Morgan Stanley, Jul 2025", tag="News", src=["ms"]),
 dict(k="2027 hyperscaler issuance (forecast)", v="~$420bn gross", d="65-75% in USD IG (Goldman)", tag="News", src=["rtGs"]),
 dict(k="Market price of AI credit", v="Median AI spread 437bp vs JNK 248bp", d="19 Nov 2026 prices", tag="News", src=["aiTracker"]),
 dict(k="'~$1.4tn, half with banks'", v="n/a", d="Informal tally at a Brookings event - not a measured estimate; not used", tag="Unverifiable", src=["brook"]),
]
grid = [
 dict(k="US utility capex 2026-30", v="~$1.3tn", d="S&P RRA $1.295tn across 46 utilities", tag="News", src=["spUtil"]),
 dict(k="Planned DC capacity facing new siting risk", v="~191 GW", d="Orennia via Utility Dive; Rystad risked delay ~1-3 GW (>10 GW if sustained)", tag="News", src=["udive","rystad"]),
 dict(k="Rates", v="+50bp floated for Dec FOMC", d="Waller, 18 Nov; use the refinancing-shock slider to see the hit to coverage", tag="News", src=["cnbcWaller"]),
 dict(k="GPU useful lives", v="5-6 yr accounting vs 1-3 yr economic", d="Nebius 4→5 yr (Reported); ECB on hyperscalers (News)", tag="Reported / News", src=["nbisFs","ecb"]),
]

discrepancies = [
 dict(t="Net debt and runway: one cash definition", d="Headline net debt and runway use unrestricted cash for every company; restricted / ring-fenced cash appears only on the project-funded basis. Hut 8 net debt $1,175m → $7,569.5m (the old figure netted $6.39bn of restricted cash and investments); Hut 8 runway 68 → ~11 months (68 on the project basis); Cipher ~1.5 months (5.4 project basis).", s="Method (audit)", src=["hutQ","cifrQ"]),
 dict(t="Post-quarter financing: strict vs pro-forma", d="Headline = strict quarter-end balances. The pro-forma toggle adds all post-quarter raises symmetrically: Nebius Citi $3.5bn, TeraWulf revolver (~$76m usable), Oracle $10bn notes + $10bn equity, Cipher $850m converts (less $165.9m exchanged), IREN ~$630m ATM, WhiteFiber $70m DDTL advance. Earlier versions counted Nebius' and TeraWulf's facilities but not Oracle's or Cipher's raises.", s="Method (audit)", src=["nbis6kCiti","wulf8kRev","orcl8k","cifrQ","irenQ","wyfi8k"]),
 dict(t="Rating bucket replaced", d="The 10-point agency bucket is now 5 points agency + 5 points market-implied cost (bond spread or, where no bonds trade, highest-rate borrowing − UST5). Hut 8 drops from 10 rating points to 7; CoreWeave from 3 to 1.", s="Method (audit)", src=["aiTracker","hutQ"]),
 dict(t="SpaceX xAI notes", d="Earlier pack listed xAI 12.5% notes; the 10-Q says they were repaid on 5 Mar 2026.", s="Corrected", src=["spcxQ"]),
 dict(t="Oracle debt after the 10-Q", d="Oracle issued $10bn notes and $10bn of common stock (86.2m shares) in early Nov 2026 (8-K), after the 31 Aug 10-Q. Headline uses 10-Q balances; the pro-forma toggle adds both.", s="Newer filing", src=["orcl8k"]),
 dict(t="Saturn size: filing vs news", d="SpaceX's 8-K (26 Oct) describes an Apollo-managed master finance lease of ~$40bn aggregate principal; Reuters reported a ~$44bn deal on 20 Nov. Filing figure used. A3 is a tranche class (Apr 2033), not a rating. Not in headline leverage until the lease commences (H1 2027).", s="Filing used", src=["spcx8kLease","rtSaturn","handoff"]),
 dict(t="IREN backlog vs RPO", d="Management's $20.3bn backlog vs $6.3bn RPO in XBRL; backlog includes lease contracts that RPO excludes.", s="Definition", src=["irenQ","irenPr"]),
 dict(t="Core Scientific capex", d="Q3 capex $985.1m in the results release (incl. land) vs $541m PP&E purchases in the 10-Q cash-flow statement. Filing figure used.", s="Filing used", src=["corzQ"]),
 dict(t="CoreWeave cash & backlog", d="$6.5bn cash on the call (incl. securities) vs $6.4bn incl. restricted / $4.1bn unrestricted in the 10-Q; $132.5bn backlog vs $132.3bn RPO.", s="Minor", src=["crwvQ","crwvPr"]),
 dict(t="Nebius EBITDA quality", d="Q3 adj. EBITDA includes $325.1m of non-recurring revenue; excluding it, leverage is ~16x rather than 4.9x - now a switchable recurring-EBITDA view.", s="Quality", src=["nbisFs"]),
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
        "TeraWulf Google backstop size; Oracle undrawn committed facilities (n/a in the 10-Q extract) and the 24-month ladder beyond the $7.6bn current portion; SpaceX ladder and undrawn lines; costs attributable to Nebius' $325.1m point-in-time revenue; CDS levels for names other than CoreWeave and Oracle; total debt for Lambda, Crusoe, Fluidstack and Together AI; Oracle full maturity ladder after the Nov notes. "
        "Street estimates not collected (management guidance used). Agency ratings come from the earlier research pack (agency/news), not filings - "
        "original links not retained. Several named-contract sizes (CoreWeave-Meta/OpenAI, Nebius-Meta, Oracle-OpenAI) are News from the earlier pack.")

edgar = dict(checked=now.strftime("%d %b %Y %H:%M SGT"),
  result=("EDGAR submissions checked for all 13 SEC registrants. No 10-Q/10-K/20-F/6-K newer than the handoff. Newer filings incorporated: "
          "Oracle 8-K (4 Nov 2026, $10bn notes + $10bn equity), Nebius 6-K (22 Oct, Citi facility), TeraWulf 8-K (23 Oct, revolver), SpaceX 8-K (26 Oct, GPU finance lease), WhiteFiber 10-Q and 8-Ks (3 and 10 Nov 2026), CoreWeave Form 144s (20 Nov 2026). "
          "Reviewed, not material to credit: Oracle 8-K Item 5.07 (20 Nov), SpaceX 8-K Item 5.02 (6 Nov), Applied Digital 8-K Item 5.07 (6 Nov), Schedule 13G/13D and Form 4 filings."),
  src=["orcl8k","nbis6kCiti","wulf8kRev","spcx8kLease","wyfiQ","wyfi8k","wyfi8kb","crwv144"])

out = dict(
  updated_iso=now.isoformat(timespec="seconds"), updated_sgt=now.strftime("%d %b %Y, %H:%M"), asof="22 Nov 2026",
  sources=S, companies=companies, agg=agg, cost=cost, news=news, earlier=earlier, upcoming=upcoming,
  scale=scale, sim=dict(factors=sim, score=simScore), telecom=telecom, verdict=verdict, macro=macro,
  discrepancies=discrepancies, claims=claims, gaps=gaps, edgar=edgar,
  audit=audit, changelog=changelog, obs=obs, holders=holders, grid=grid,
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
for r in changelog: print(f"{r['name']:18} {r['old']} -> {r['new']} (pf {r['pf']}) | {r['note']}")
