/* Neocloud credit engine - the single source of the credit math (browser + node).
   All money in USD m. Settings:
   basis: 'corp' (unrestricted cash only, default) | 'proj' (adds restricted / ring-fenced cash)
   fin:   'strict' (quarter-end, default) | 'pf' (adds post-quarter raises)
   debt:  'headline' (default) | 'lease' (adds on-balance-sheet lease liabilities; EBITDAR and rent-adjusted cover)
   ebitda:'reported' (default) | 'recurring' (Nebius ex point-in-time strategic-partnership revenue)
   hair:  GPU shock 0..0.40
   shock: refinancing shock in bp 0..600
   delay: capex delay in months 0..12
   refiClosed: HY refinancing window closed (2026-27 HY maturities paid from cash/equity)
   undrawnHair: 0..1 haircut to committed undrawn (null = derive from rules)
   prepayFreeze: 0..1 freeze of disclosed expected prepayments (null = derive: 0/0.25/0.50/1.00)

   Base (all stresses zero) is unchanged. Stressed P&L uses tier-specific channels
   documented in NCE.ASSUMPTIONS (external review vs our rubric vs filings). */
(function(root){
const BASE={basis:'corp',fin:'strict',debt:'headline',ebitda:'reported',hair:0,shock:0,delay:0,refiClosed:false,undrawnHair:null,prepayFreeze:null};
const ptsL=(l,E)=>(l==null||E==null||E<=0)?0:l<=3?30:l<=5?22:l<=8?14:l<=12?7:0;
const ptsC=c=>c==null?0:c>=5?25:c>=3?18:c>=2?12:c>=1?6:0;
const ptsR=(r,self)=>self?20:r==null?0:r>=24?20:r>=12?14:r>=6?8:3;
const ptsM=s=>s==null?0:s<=150?5:s<=250?4:s<=350?3:s<=500?2:s<=800?1:0;

/* Stress profiles. Dollar figures in USD m. Shares are 0-1. */
const PROF={
  crwv:{role:'neocloud',contracted:1,contractedHow:'our rubric: no uncontracted share disclosed; current revenue treated as contracted given RPO $132.3bn',drop:0.85,prepay:9000,prepayLbl:'~$9bn expected in the next 3 months · Mgmt (10 Nov)',gpuDdtl:17700,incArr:6700,incArrLbl:'Calc from Mgmt: exit-2026 run-rate $20bn less FY26 guide $13.3bn (low ends)'},
  nbis:{role:'neocloud',contracted:1,contractedHow:'our rubric: no uncontracted share disclosed; current revenue treated as contracted given RPO $38.7bn',drop:0.85,prepay:10000,prepayLbl:'~$10bn in 2026 · Mgmt (Q3 call). 2027 $17-20bn range is not added to the freeze (range, not a point).',gpuDdtl:0},
  iren:{role:'neocloud',contracted:0,contractedHow:'company label: all current revenue (AI cloud + bitcoin) is market-priced; Microsoft share is of backlog, not of current revenue',drop:0.85,prepay:0,gpuDdtl:1720,incArr:4000,incArrLbl:'>$4bn ARR from Jan 2027 · Mgmt'},
  orcl:{role:'hyperscaler',slice:0.382,sliceLbl:'Cloud infrastructure $7,388m of $19,345m Q1 FY27 · Reported',drop:0.65,prepay:0,gpuDdtl:0},
  spcx:{role:'hyperscaler',slice:0.482,sliceLbl:'SI (Solutions & Infrastructure, incl. AI) $7,022m of $14,575m · Reported',drop:0.65,dropHow:'our rubric: review did not specify SpaceX; we use the same 65% drop-through as Oracle',prepay:0,gpuDdtl:0,ourRubric:true},
  apld:{role:'landlord',nonIg:0.28,nonIgLbl:'CoreWeave anchors Polaris Forge 1: 400 MW of ~1.41 GW ≈ 28% · Mgmt/Calc; rest IG hyperscalers',drop:0.90,tenant:'CoreWeave',energise:1.3,energiseLbl:'300 MW and Polaris Forge 2 initial ops by end-2026 · Mgmt → 1.3 months from 22 Nov 2026 · Calc',prepay:0,gpuDdtl:0},
  cifr:{role:'landlord',nonIg:0,nonIgLbl:'Barber Lake Google-backstopped · Reported; other contract values n/a',drop:0.90,energise:2.5,energiseLbl:'Barber Lake Q4 2026-Q1 2027 · Mgmt → mid-window 2.5 months from 22 Nov 2026 · Calc',prepay:0,gpuDdtl:0},
  wulf:{role:'landlord',nonIg:0,nonIgLbl:'Justified / Fluidstack leases have a Google credit backstop · Reported; size n/a',drop:0.90,energise:1.3,energiseLbl:'CB-4 Q4 2026 · Mgmt → 1.3 months to YE2026 · Calc',prepay:0,gpuDdtl:0},
  hut:{role:'landlord',nonIg:0,nonIgLbl:'River Bend Fluidstack/Anthropic with Google backstop; Beacon Point 2 unnamed high-IG tenant · Mgmt',drop:0.90,energise:5.8,energiseLbl:'River Bend Q2 2027 · Mgmt → 5.8 months to mid-May 2027 · Calc',prepay:0,gpuDdtl:0},
  corz:{role:'landlord',nonIg:0.42,nonIgLbl:'CoreWeave 590 MW (~$10bn) ≈ 42% of >$24bn contracted · Mgmt/Calc; AMD-backed 530 MW is not in the non-IG share',drop:0.90,tenant:'CoreWeave',energise:2.3,energiseLbl:'Remaining CoreWeave sites early 2027 · Mgmt → 2.3 months to mid-Jan 2027 · Calc',prepay:0,gpuDdtl:0},
  wyfi:{role:'landlord',nonIg:1,nonIgLbl:'Nscale (unrated) is the sole NC-1 tenant · Reported',drop:0.90,tenant:'Nscale',energise:null,energiseLbl:'NC-1 already operational (Nov 2026); MTL-2 energisation date n/a',early:true,prepay:0,gpuDdtl:0}
};

const ASSUMPTIONS=[
  {tag:'Assumption (external review)',t:'GPU neoclouds (CoreWeave, Nebius, I-Ren): revenue shock = (slider/40%) × (100% of uncontracted revenue + 35% of contracted revenue, mid-point of the 25-50% range); 85% EBITDA drop-through.'},
  {tag:'Assumption (our rubric)',t:'No uncontracted share is disclosed for CoreWeave or Nebius; current revenue is treated as contracted. I-Ren current revenue is treated as uncontracted/market-priced, per the company label.'},
  {tag:'Assumption (external review)',t:'Powered-shell landlords: no direct price hit on IG or Google-backstopped leases. The revenue hit is non-IG tenant default risk × slider/40%, with 90% drop-through (lower bound of the 90-95% range). Their main channel is the Delay slider.'},
  {tag:'Assumption (external review)',t:'Oracle: shock applies only to the OCI / cloud-infrastructure slice, 38.2% of Q1 FY27 revenue ($7,388m of $19,345m · Reported), with 65% drop-through.'},
  {tag:'Assumption (our rubric)',t:'SpaceX was not in the external review. Shock applies to the reported SI slice (48.2%) with the same 65% hyperscaler drop-through.'},
  {tag:'Assumption (external review)',t:'Undrawn facilities: 0% Base/Mild, 50% Severe, 100% Crisis; and at least 50% whenever stressed coverage is below 1.5x or delay exceeds 3 months (100% in Crisis).'},
  {tag:'Assumption (external review)',t:'Prepayment freeze −25/−50/−100% by Mild/Severe/Crisis, applied only to verified CoreWeave (~$9bn, 3 months · Mgmt) and Nebius (~$10bn in 2026 · Mgmt) figures. Nebius 2027 $17-20bn is a range and is not included in the freeze dollars.'},
  {tag:'Assumption (external review)',t:'Delay penalties: 2 days of rent credit per day late, applied only where incremental ARR is disclosed (CoreWeave, I-Ren). Termination risk flagged from 9 months; RPO at-risk 20% at 12 months (that 20% is our rubric — the review was truncated).'},
  {tag:'Assumption (our rubric)',t:'GPU-collateral LTV sweeps: the review named the channel but not the size (triggers are not disclosed). For GPU-DDTL borrowers (CoreWeave, I-Ren), usable unrestricted cash is reduced by 25% × (slider/40%).'},
  {tag:'Assumption (external review)',t:'Reflexive equity haircut: stressed market cap = current × (1 − 1.5 × GPU shock), floored at 20%. Dilution above 50% flags Unfinanceable / Restructuring. Market caps are not in this dataset, so mcap, dilution % and the 35% solvency test are n/a.'},
  {tag:'Assumption (external review)',t:'HY refinancing window closed: 2026-27 maturities of non-IG names must be paid from cash or equity (cannot roll). IG names (Oracle, SpaceX; Hut 8 on its project-note class) can still refinance.'},
  {tag:'Assumption (external review)',t:'Implied rating bands: 80-100 BBB, 65-79 BB, 45-64 B, 25-44 CCC, below 25 CC/D. Hard caps only worsen a bucket: BB if lease-adjusted net leverage > 4x or 5-year CDS > 250bp; B if 24-month cover < 1x; CCC if (runway < 6 months and 24-month cover < 0.75x) or (EBITDA/interest < 1x, operating names only). Our rubric (review truncated): CC/D if the closed window leaves 12-month maturities unpaid from cash, or if an operating name has coverage < 1x and runway < 3 months. Construction-phase names use project-funded runway vs months to energisation instead of the coverage cap.'}
];

function isStressed(st){return !!(st.hair||st.shock||st.delay||st.refiClosed);}
function deriveUndrawn(st,cov){
  if(st.undrawnHair!=null)return Math.min(1,Math.max(0,st.undrawnHair));
  if(!isStressed(st))return 0; /* never haircut undrawn on the headline / Base case */
  let u=0;
  if(st.hair>=0.40||st.delay>=12)u=1;
  else if(st.hair>=0.25||st.shock>=250)u=0.5;
  if((cov!=null&&cov<1.5)||st.delay>3)u=Math.max(u,0.5);
  if(st.hair>=0.40||st.delay>=12)u=1;
  return u;
}
function deriveFreeze(st){
  if(st.prepayFreeze!=null)return Math.min(1,Math.max(0,st.prepayFreeze));
  if(!isStressed(st))return 0;
  if(st.hair>=0.40||st.delay>=12)return 1;
  if(st.hair>=0.25||st.shock>=250||st.delay>=6)return 0.5;
  if(st.hair>=0.10||st.shock>=100||st.delay>=3)return 0.25;
  return 0;
}

function pnlHit(c,st){
  /* Returns quarterly revenue loss and EBITDA/OCF loss (USD m). Zero at base. */
  const i=c.inp,p=PROF[c.id],revQ=i.rev_q||0,s=st.hair||0;
  if(!s||!p||!revQ)return {revHitQ:0,ebitdaHitQ:0,how:'none'};
  const scale=s/0.40;
  if(p.role==='neocloud'){
    const uShare=1-(p.contracted||0),cShare=p.contracted||0;
    const hair=uShare*(1.00*scale)+cShare*(0.35*scale);
    const revHitQ=hair*revQ,ebitdaHitQ=(p.drop||0.85)*revHitQ;
    return {revHitQ,ebitdaHitQ,how:'neocloud',hair,scale};
  }
  if(p.role==='hyperscaler'){
    const revHitQ=s*(p.slice||0)*revQ,ebitdaHitQ=(p.drop||0.65)*revHitQ;
    return {revHitQ,ebitdaHitQ,how:'hyperscaler',scale};
  }
  if(p.role==='landlord'){
    const revHitQ=scale*(p.nonIg||0)*revQ,ebitdaHitQ=(p.drop||0.90)*revHitQ;
    return {revHitQ,ebitdaHitQ,how:'landlord-tenant',scale};
  }
  return {revHitQ:0,ebitdaHitQ:0,how:'none'};
}

function calc(c,st){
  st=Object.assign({},BASE,st||{});const i=c.inp;if(!i)return null;
  const pf=(st.fin==='pf'&&c.pf)?c.pf:{};
  const lease=st.debt==='lease';
  const p=PROF[c.id]||{};
  let eq=(i.ebitda_q!=null?i.ebitda_q:i.ttm_ebitda/4);
  if(st.ebitda==='recurring'&&i.recur_adj_q)eq+=i.recur_adj_q;
  const hitPnl=pnlHit(c,st);
  /* Legacy 1-for-1 GPU haircut is replaced by tier-specific drop-through when a profile exists.
     Names without a profile (none of the 11 scored) fall back to the old hair*gpu*rev path. */
  const legacy=(!PROF[c.id])?st.hair*(i.gpu||0)*(i.rev_q||0):0;
  const ebitdaHitQ=hitPnl.ebitdaHitQ+legacy;
  const ocfHitQ=ebitdaHitQ; /* same drop-through applied to OCF · our rubric */
  eq-=ebitdaHitQ;
  const rentQ=lease?(i.oplc_q||0):0;
  const E=4*(eq+rentQ);
  const m24Known=i.m24!=null,m24=m24Known?i.m24+(pf.m24||0):null;
  const shockI=(st.shock/1e4)*(m24||0);
  const I=(i.ttm_int?i.ttm_int:4*i.int_q)+shockI+4*rentQ;
  const debt=i.debt+(pf.debt||0)+(lease?(i.leases||0):0);
  const cashND=i.cash_u+(st.basis==='proj'?(i.cash_r||0):0)+(pf.cash||0);
  const nd=debt-cashND,lev=E>0?nd/E:null;
  const cov=I>0?E/I:null;
  const ecx=(eq-i.capex_q)/((i.ttm_int?i.ttm_int:4*i.int_q)/4+shockI/4);
  const burn=(i.capex_q-(i.ocf_q||0)+ocfHitQ+shockI/4)/3;
  const undrawnH=deriveUndrawn(st,cov);
  const freeze=deriveFreeze(st);
  const prepayAmt=p.prepay||0,prepayHit=freeze*prepayAmt;
  const scale=st.hair?st.hair/0.40:0;
  const sweep=(!scale||!p.gpuDdtl)?0:Math.min(i.cash_u,i.cash_u*0.25*scale);
  const delayCost=st.delay*Math.max(burn,0);
  const penalty=(!st.delay||!p.incArr)?0:2*(st.delay/12)*p.incArr; /* 2-for-1 rent credit on incremental ARR, annualised $ */
  const rpoRisk=(st.delay>=12&&c.backlog!=null)?0.20*c.backlog*1000:0; /* USD m, 20% of $bn backlog; display only */
  const termRisk=st.delay>=9;
  const undrawnUse=(i.undrawn+(pf.undrawn||0))*(1-undrawnH);
  const liq0=i.cash_u+undrawnUse+(pf.cash||0)-sweep-prepayHit;
  const liqBasis=liq0+(st.basis==='proj'?(i.cash_r||0):0);
  const liq=liqBasis-delayCost-penalty;
  const self=burn<=0;
  const run=self?null:Math.max(liq,0)/burn;
  const runCorp=self?null:Math.max(liq0-delayCost-penalty,0)/burn;
  const runProj=self?null:Math.max(liq0+(i.cash_r||0)-delayCost-penalty,0)/burn;
  const m24cov=(m24&&m24>0)?Math.max(liq,0)/m24:null;
  /* 12-month wall in $m from the calendar ladder when we have one */
  const wall12=(c.wall&&c.wall[0]!=null)?c.wall[0]*1000:null;
  const wall24=(c.wall&&c.wall[0]!=null&&c.wall[1]!=null)?(c.wall[0]+c.wall[1])*1000:m24;
  const hy=c.ratingClass!=='IG';
  const mustPay=(st.refiClosed&&hy)?(wall24!=null?wall24:(m24||0)):0;
  /* Funding gap (Calc): 24-month (or, if the HY window is closed, 2026-27 HY) principal
     + delay cash cost + delay penalties − usable liquidity (already net of undrawn haircut, LTV sweep and prepay freeze).
     If the 24-month wall is undisclosed, only delay/penalty/mustPay count and gapM24na is true. */
  const due=m24Known?Math.max(m24||0,mustPay):mustPay;
  const gapFinal=Math.max(0,due+delayCost+penalty-liqBasis);
  const mk=c.mkt&&c.mkt.spread!=null?c.mkt.spread:null;
  const P={L:ptsL(lev,E),C:ptsC(cov),R:ptsR(run,self),Q:i.Q,A:i.A5,M:ptsM(mk)};
  const score=P.L+P.C+P.R+P.Q+P.A+P.M;
  const revQ0=i.rev_q,revQ=revQ0==null?null:revQ0-hitPnl.revHitQ;
  const rev=revQ==null?null:4*revQ,rev0=revQ0==null?null:4*revQ0;
  const fcfQ=(i.ocf_q||0)-i.capex_q-ocfHitQ-shockI/4,fcf=4*fcfQ;
  return {E,eq,I,debt,nd,lev,cov,ecx,burn,liq,liqBasis,run,runCorp,runProj,self,m24,m24cov,P,score,
    hit:ebitdaHitQ,shockI,delayCost,revQ,rev,rev0,fcfQ,fcf,gap:gapFinal,gapM24na:!m24Known,
    gpu:i.gpu||0,undrawnH,freeze,prepayHit,sweep,penalty,rpoRisk,termRisk,wall12,wall24,mustPay,hy,
    hitPnl,revHitQ:hitPnl.revHitQ,ebitdaHitQ,ocfHitQ,due,
    note:`Leverage ${P.L} + Coverage ${P.C} + Runway ${P.R} + Counterparty ${P.Q} + Agency ${P.A} + Market ${P.M} = ${score}`};
}

const api={BASE,calc,ptsL,ptsC,ptsR,ptsM,PROF,ASSUMPTIONS,deriveUndrawn,deriveFreeze,pnlHit};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NCE=api;
})(typeof window!=='undefined'?window:globalThis);
