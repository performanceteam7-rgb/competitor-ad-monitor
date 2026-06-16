// 네이버웹툰 9건 제목/장르 정정 (LLM 분류)
const fs=require("fs"),path=require("path");
const base=path.join(__dirname,"..");
const C={
 "meta_1297455529092031":["다정한 침입자","로맨스","female"],
 "meta_1479707630093806":["쪽팔려 게임","스릴러","all"],
 "meta_1036718878689367":["쪽팔려 게임","스릴러","all"],
 "meta_1006734975625049":["양아치의 첫사랑","로맨스","female"],
 "meta_1719787902805163":["우리 길드 아이돌","판타지","all"],
 "meta_1499818514951740":["쪽팔려 게임","스릴러","all"],
 "meta_2548463125570388":["쪽팔려 게임","스릴러","all"],
 "meta_891648973207666":["이섭의 연애","로맨스","female"],
 "meta_2772590149806880":["해시태그는 첫사랑","로맨스","female"],
};
const code=fs.readFileSync(path.join(base,"data.js"),"utf8");
const window={}; eval(code);
let n=0;
for(const c of window.AD_DATA.creatives){ const m=C[c.id]; if(m){c.work_title=m[0];c.genre=m[1];c.gender=m[2];c.title_conf="정확";n++;} }
fs.writeFileSync(path.join(base,"data.js"),"/* AUTO-GENERATED + LLM 보정 */\nwindow.AD_DATA = "+JSON.stringify(window.AD_DATA,null,2)+";\n");
console.log("네이버 보정:",n);
