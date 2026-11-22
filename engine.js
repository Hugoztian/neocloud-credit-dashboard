/* Neocloud credit engine - the single source of the credit math (browser + node).
   All money in USD m. Settings:
   basis: 'corp' (unrestricted cash only, default) | 'proj' (adds restricted / ring-fenced cash)
   fin:   'strict' (quarter-end, default) | 'pf' (adds post-quarter raises)
   debt:  'headline' (default) | 'lease' (adds on-balance-sheet lease liabilities; EBITDAR and rent-adjusted cover)
   ebitda:'reported' (default) | 'recurring' (Nebius ex point-in-time strategic-partnership revenue)
   hair:  GPU revenue haircut 0..0.40   shock: refinancing shock in bp 0..400   delay: capex delay in months 0..6 */
(function(root){
const BASE={basis:'corp',fin:'strict',debt:'headline',ebitda:'reported',hair:0,shock:0,delay:0};
const ptsL=(l,E)=>(l==null||E==null||E<=0)?0:l<=3?30:l<=5?22:l<=8?14:l<=12?7:0;
const ptsC=c=>c==null?0:c>=5?25:c>=3?18:c>=2?12:c>=1?6:0;
const ptsR=(r,self)=>self?20:r==null?0:r>=24?20:r>=12?14:r>=6?8:3;
const ptsM=s=>s==null?0:s<=150?5:s<=250?4:s<=350?3:s<=500?2:s<=800?1:0;
function calc(c,st){
  st=Object.assign({},BASE,st||{});const i=c.inp;if(!i)return null;
  const pf=(st.fin==='pf'&&c.pf)?c.pf:{};
  const lease=st.debt==='lease';
  let eq=(i.ebitda_q!=null?i.ebitda_q:i.ttm_ebitda/4);
  if(st.ebitda==='recurring'&&i.recur_adj_q)eq+=i.recur_adj_q;
  const hit=st.hair*(i.gpu||0)*(i.rev_q||0);           // quarterly EBITDA and OCF lost to the revenue haircut
  eq-=hit;
  const rentQ=lease?(i.oplc_q||0):0;
  const E=4*(eq+rentQ);                                   // run-rate EBITDA (EBITDAR in lease view)
  const m24=(i.m24==null?null:i.m24+(pf.m24||0));
  const shockI=(st.shock/1e4)*(m24||0);                   // extra annual interest on debt refinanced within 24 months
  const I=(i.ttm_int?i.ttm_int:4*i.int_q)+shockI+4*rentQ;
  const debt=i.debt+(pf.debt||0)+(lease?(i.leases||0):0);
  const cashND=i.cash_u+(st.basis==='proj'?(i.cash_r||0):0)+(pf.cash||0);
  const nd=debt-cashND, lev=E>0?nd/E:null;
  const cov=I>0?E/I:null;
  const ecx=(eq-i.capex_q)/((i.ttm_int?i.ttm_int:4*i.int_q)/4+shockI/4);
  const burn=(i.capex_q-i.ocf_q+hit+shockI/4)/3;          // monthly cash burn
  const liq0=i.cash_u+i.undrawn+(pf.cash||0)+(pf.undrawn||0);
  const liqBasis=liq0+(st.basis==='proj'?(i.cash_r||0):0);
  const delayCost=st.delay*Math.max(burn,0);              // each month of delay = a month of burn before new revenue
  const liq=liqBasis-delayCost, self=burn<=0;
  const run=self?null:Math.max(liq,0)/burn;
  const runCorp=self?null:Math.max(liq0-delayCost,0)/burn;
  const runProj=self?null:Math.max(liq0+(i.cash_r||0)-delayCost,0)/burn;
  const m24cov=(m24&&m24>0)?Math.max(liq,0)/m24:null;
  const mk=c.mkt&&c.mkt.spread!=null?c.mkt.spread:null;
  const P={L:ptsL(lev,E),C:ptsC(cov),R:ptsR(run,self),Q:i.Q,A:i.A5,M:ptsM(mk)};
  const score=P.L+P.C+P.R+P.Q+P.A+P.M;
  return {E,eq,I,debt,nd,lev,cov,ecx,burn,liq,run,runCorp,runProj,self,m24,m24cov,P,score,
    note:`Leverage ${P.L} + Coverage ${P.C} + Runway ${P.R} + Counterparty ${P.Q} + Agency ${P.A} + Market ${P.M} = ${score}`};
}
const api={BASE,calc,ptsL,ptsC,ptsR,ptsM};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NCE=api;
})(typeof window!=='undefined'?window:globalThis);
