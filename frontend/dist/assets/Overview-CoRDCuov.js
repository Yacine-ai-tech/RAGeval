import{a as i,j as e}from"./motion-CKsw07PI.js";import{c as r,a as x,P as f,S as k,C as g,b as j,d as l,e as b,E as A,L as S,A as L,f as w}from"./index-38xpu3I-.js";import{R as C,L as _,C as z,X as N,Y as F,T as E,a as M,b as c}from"./charts-Dfe1oyhB.js";/**
 * @license lucide-react v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const R=r("Activity",[["path",{d:"M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2",key:"169zse"}]]);/**
 * @license lucide-react v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const T=r("Clock3",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["polyline",{points:"12 6 12 12 16.5 12",key:"1aq6pp"}]]);/**
 * @license lucide-react v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const q=r("Database",[["ellipse",{cx:"12",cy:"5",rx:"9",ry:"3",key:"msslwz"}],["path",{d:"M3 5V19A9 3 0 0 0 21 19V5",key:"1wlel7"}],["path",{d:"M3 12A9 3 0 0 0 21 12",key:"mv7ke4"}]]);/**
 * @license lucide-react v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const D=r("Flag",[["path",{d:"M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z",key:"i9b6wo"}],["line",{x1:"4",x2:"4",y1:"22",y2:"15",key:"1cm3nv"}]]);/**
 * @license lucide-react v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const $=r("ShieldCheck",[["path",{d:"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z",key:"oel41y"}],["path",{d:"m9 12 2 2 4-4",key:"dzmm74"}]]);/**
 * @license lucide-react v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const G=r("Target",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["circle",{cx:"12",cy:"12",r:"6",key:"1vlfrh"}],["circle",{cx:"12",cy:"12",r:"2",key:"1c9p78"}]]);function P(){const[o,m]=i.useState("7"),[t,d]=i.useState(null),[n,y]=i.useState(null),[u,h]=i.useState("");i.useEffect(()=>{d(null),Promise.all([x.metrics(Number(o)),x.queries(200)]).then(([a,s])=>{d(a),y(s)}).catch(a=>h(String(a)))},[o]);const v=i.useMemo(()=>n?[...n].reverse().map((s,p)=>({i:p+1,label:new Date(s.timestamp).toLocaleDateString(void 0,{month:"short",day:"numeric"}),relevance:s.relevance,groundedness:s.groundedness,faithfulness:s.faithfulness})):[],[n]);return e.jsxs("div",{children:[e.jsx(f,{title:"Overview",sub:"Quality, cost and reliability of every tracked RAG interaction, scored by the multi-judge evaluation pipeline.",actions:e.jsx(k,{value:o,onChange:m,options:[{value:"7",label:"Last 7 days"},{value:"30",label:"Last 30 days"},{value:"90",label:"Last 90 days"}]})}),u&&e.jsx(g,{children:e.jsx("div",{className:"text-sm text-bad",children:u})}),t?e.jsxs(e.Fragment,{children:[e.jsxs("div",{className:"grid gap-4 sm:grid-cols-2 xl:grid-cols-4",children:[e.jsx(l,{label:"Tracked queries",value:t.total_queries,icon:q,sub:`last ${o} days`}),e.jsx(l,{label:"Avg retrieval relevance",value:t.avg_relevance.toFixed(2),icon:G,delta:{text:t.avg_relevance>=.75?"healthy":"below threshold",good:t.avg_relevance>=.75}}),e.jsx(l,{label:"Avg groundedness",value:t.avg_groundedness.toFixed(2),icon:$,delta:{text:t.avg_groundedness>=.75?"healthy":"review",good:t.avg_groundedness>=.75}}),e.jsx(l,{label:"Flagged for review",value:t.flagged_count,icon:D,delta:t.flagged_count>0?{text:"needs attention",good:!1}:{text:"all clear"}})]}),e.jsxs("div",{className:"mt-4 grid gap-4 sm:grid-cols-3",children:[e.jsx(l,{label:"Avg faithfulness",value:t.avg_faithfulness.toFixed(2),icon:R}),e.jsx(l,{label:"Avg latency",value:`${Math.round(t.avg_latency_ms)} ms`,icon:T}),e.jsx(l,{label:"Total cost",value:`$${t.total_cost_usd.toFixed(4)}`,icon:b,sub:`last ${o} days`})]})]}):e.jsx("div",{className:"grid gap-4 sm:grid-cols-2 xl:grid-cols-4",children:Array.from({length:4}).map((a,s)=>e.jsx(j,{className:"h-28"},s))}),e.jsx(g,{title:"Quality per tracked query",className:"mt-5",actions:e.jsx(w,{title:"derived client-side from the real query log",children:"query log"}),children:v.length===0?e.jsx(A,{title:"No tracked interactions yet",hint:"Score one on the Evaluate page or instrument your RAG app with the @track decorator.",action:e.jsxs(S,{className:"text-sm underline decoration-dotted text-dim hover:text-body",to:"/evaluate",style:{display:"inline-flex",alignItems:"center",gap:4},children:["Open Evaluate ",e.jsx(L,{size:12})]})}):e.jsx("div",{className:"h-[300px]",children:e.jsx(C,{width:"100%",height:"100%",children:e.jsxs(_,{data:v,margin:{top:8,right:8,left:-22,bottom:0},children:[e.jsx(z,{stroke:"var(--grid-line)",vertical:!1}),e.jsx(N,{dataKey:"label",tick:{fill:"var(--text-muted)",fontSize:11},axisLine:{stroke:"var(--border)"},tickLine:!1,minTickGap:40}),e.jsx(F,{domain:[0,1],tick:{fill:"var(--text-muted)",fontSize:11},axisLine:!1,tickLine:!1}),e.jsx(E,{contentStyle:{background:"var(--surface-2)",border:"1px solid var(--border-strong)",borderRadius:12,color:"var(--text)",fontSize:12},formatter:a=>[typeof a=="number"?a.toFixed(3):"—"]}),e.jsx(M,{wrapperStyle:{fontSize:11,color:"var(--text-2)"}}),e.jsx(c,{type:"monotone",dataKey:"relevance",stroke:"var(--accent)",dot:!1,strokeWidth:2,isAnimationActive:!1}),e.jsx(c,{type:"monotone",dataKey:"groundedness",stroke:"var(--accent-2)",dot:!1,strokeWidth:2,isAnimationActive:!1}),e.jsx(c,{type:"monotone",dataKey:"faithfulness",stroke:"var(--success)",dot:!1,strokeWidth:1.5,strokeDasharray:"4 3",isAnimationActive:!1})]})})})})]})}export{P as default};
