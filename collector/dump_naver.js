const fs=require("fs"),path=require("path");
const code=fs.readFileSync(path.join(__dirname,"..","data.js"),"utf8");
const window={}; eval(code);
const nv=window.AD_DATA.creatives.filter(c=>c.competitor==="네이버웹툰");
console.log(JSON.stringify(nv.map(c=>({id:c.id,t:c.work_title,g:c.genre,copy:c.copy})),null,1));
