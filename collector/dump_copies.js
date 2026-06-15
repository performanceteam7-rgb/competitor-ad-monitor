// data.js에서 분류용 최소 필드만 추출 → JSON 출력
const fs = require("fs");
const path = require("path");
const base = path.join(__dirname, "..");
const code = fs.readFileSync(path.join(base, "data.js"), "utf8");
const window = {};
eval(code);
const out = window.AD_DATA.creatives.map(c => ({
  id: c.id, competitor: c.competitor, copy: (c.copy||"").replace(/\s+/g," ").trim(),
  cur_title: c.work_title, cur_genre: c.genre, cur_gender: c.gender
}));
fs.writeFileSync(path.join(__dirname, "copies.json"), JSON.stringify(out, null, 1));
console.log("dumped", out.length);
