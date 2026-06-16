const fs=require("fs"),path=require("path");
const code=fs.readFileSync(path.join(__dirname,"..","data.js"),"utf8");
const window={}; eval(code);
const cs=window.AD_DATA.creatives;
const byP={};
for(const c of cs){ (byP[c.competitor]=byP[c.competitor]||{})[c.work_title]=(byP[c.competitor][c.work_title]||0)+1; }
const order=["네이버웹툰","카카오페이지","리디","넷플릭스","티빙","웨이브","쿠팡플레이","디즈니+"];
for(const p of order){
  if(!byP[p]) continue;
  const top=Object.entries(byP[p]).sort((a,b)=>b[1]-a[1]).slice(0,3);
  console.log(p, "→", top.map(t=>`${t[0]}(${t[1]})`).join(", "));
}
