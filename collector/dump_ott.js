const fs=require("fs"),path=require("path");
const base=path.join(__dirname,"..");
const code=fs.readFileSync(path.join(base,"data.js"),"utf8");
const window={}; eval(code);
const cs=window.AD_DATA.creatives;
const wt=cs.filter(c=>c.category==="웹툰");
const ott=cs.filter(c=>c.category==="OTT");
const stats={
  webtoon_total: wt.length,
  webtoon_misang: wt.filter(c=>c.work_title==="(미상)").length,
  webtoon_gita: wt.filter(c=>c.genre==="기타").length,
  ott_total: ott.length,
};
// OTT: 플랫폼별 dedupe된 copy 목록 (분류용)
const seen=new Set(), ottList=[];
for(const c of ott){ const k=c.competitor+"|"+c.copy.slice(0,40); if(seen.has(k))continue; seen.add(k);
  ottList.push({id:c.id, p:c.competitor, t:c.work_title, copy:c.copy}); }
fs.writeFileSync(path.join(__dirname,"ott_copies.json"), JSON.stringify({stats, ott:ottList},null,1));
console.log(JSON.stringify(stats));
console.log("ott distinct:", ottList.length);
