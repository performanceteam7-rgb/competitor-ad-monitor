# -*- coding: utf-8 -*-
"""
경쟁사 광고 소재 수집기 (production)
- Meta 광고 라이브러리에서 카카오페이지/리디/네이버웹툰 광고를 수집
- 카루셀 dedupe(라이브러리 ID 기준) · 대표 이미지 다운로드 · 성향/장르 휴리스틱 분류
- ../data.js 재생성 + history 스냅샷 누적(WoW용)

실행: browser-harness 컨텍스트에서 stdin으로 실행 (new_tab/js/wait_for_load 사용)
  $env:PYTHONIOENCODING="utf-8"
  cmd /c "C:\\Users\\<user>\\.local\\bin\\browser-harness.exe < run_collect.py"

주의: Meta 광고 라이브러리는 공개(로그인 불필요). 키워드 검색은 제3자 광고가 섞이므로
      advertiser 화이트리스트 토큰으로 필터링한다.
"""
import sys, os, re, json, base64, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = r"C:\Users\MADUP\competitor-ad-monitor"
ASSETS = os.path.join(BASE, "assets")
HISTORY = os.path.join(BASE, "collector", "history")
os.makedirs(ASSETS, exist_ok=True)
os.makedirs(HISTORY, exist_ok=True)

TODAY = os.environ.get("BH_TODAY", "2026-06-11")  # run_weekly.ps1이 BH_TODAY로 주입

# ---- 수집 대상 (경쟁사 + 우리) -----------------------------------------
# advertiser_tokens: 해당 토큰을 광고주명에 포함하면 그 사업자 광고로 인정 (제3자 노이즈 제거)
# q+advertiser_tokens = 키워드 검색(제3자 필터), page_id = 특정 페이지 전체(노이즈 0)
# category: 웹툰 | OTT
TARGETS = [
    # ── 웹툰/웹소설 경쟁사 ──
    {"competitor": "카카오페이지", "category":"웹툰", "q": "카카오페이지",
     "advertiser_tokens": ["kakaopage", "kakao.entertainment", "kakaoent", "kakao_page", "카카오페이지"]},
    {"competitor": "리디",         "category":"웹툰", "q": "리디북스",
     "advertiser_tokens": ["ridi", "리디"]},
    {"competitor": "리디",         "category":"웹툰", "q": "리디",
     "advertiser_tokens": ["ridi", "리디"]},
    # 자사: 공식 페이지(facebook.com/nwebtoon) — page_id 기반(정밀) + 키워드 검색(경쟁사와 동일 기준, 다른 계정/서브페이지 소재까지 포괄)
    {"competitor": "네이버웹툰",   "category":"웹툰", "page_id": "700492680053373"},
    {"competitor": "네이버웹툰",   "category":"웹툰", "q": "네이버웹툰",
     "advertiser_tokens": ["네이버웹툰", "webtoon", "naver webtoon", "nwebtoon", "line webtoon"]},
    # ── OTT (page_id 기반, 공식 페이지 전체) ──
    {"competitor": "넷플릭스",     "category":"OTT", "page_id": "927701797321428"},
    {"competitor": "티빙",         "category":"OTT", "page_id": "157630184278168"},
    {"competitor": "웨이브",       "category":"OTT", "page_id": "1470492576566418"},
    {"competitor": "쿠팡플레이",   "category":"OTT", "page_id": "100649765217814"},
    {"competitor": "디즈니+",      "category":"OTT", "page_id": "319549278583533"},
]

# ---- 분류 사전 (휴리스틱 → confidence '추정') ---------------------------
KW_FEMALE = ["로맨스","로판","여주","황후","황녀","황비","영애","공녀","결혼","재혼","빙의","악녀",
             "BL","남주","설렘","첫사랑","신데렐라","계약","집착","후회","순정","웨딩","키스","연애"]
KW_MALE   = ["헌터","레벨업","회귀","무림","무협","검","사냥","랭커","던전","영지","플레이어","각성",
             "소드마스터","게임","용병","귀환","최강","전생","마탑","기사단","아카데미"]
GENRE_RULES = [
    ("BL",     ["BL","남남","비엘"]),
    ("로판",   ["황제","황후","황녀","황비","영애","공작","공녀","빙의","악녀","제국","기사","귀족","후작"]),
    ("로맨스", ["연애","결혼","사내","첫사랑","썸","설렘","재혼","웨딩","계약연애"]),
    ("무협",   ["무림","무공","화산","사파","정파","검신","천마","무협"]),
    ("액션",   ["헌터","레벨업","각성","던전","랭커","소드","사냥","용병","최강"]),
    ("판타지", ["마법","마탑","영지","회귀","전생","귀환","아카데미","플레이어","게임"]),
    ("일상",   ["일상","힐링","개그","코믹","먹방","강아지","고양이"]),
    ("드라마", ["복수","비밀","재벌","오피스","데뷔","아이돌"]),
]

# ---- 주요 작품 사전 (정확 매칭 → title·gender·genre 확정) -------------
# 형식: 정규화된 키워드(공백제거) : (정식제목, gender, genre)
KNOWN_WORKS = {
    "나혼자만레벨업": ("나 혼자만 레벨업","male","액션"),
    "나노마신": ("나노마신","male","무협"),
    "화산귀환": ("화산귀환","male","무협"),
    "검술명가막내아들": ("검술명가 막내아들","male","판타지"),
    "템빨": ("템빨","male","판타지"),
    "전지적독자시점": ("전지적 독자 시점","male","판타지"),
    "사내맞선": ("사내맞선","female","로맨스"),
    "내남편과결혼해줘": ("내 남편과 결혼해줘","female","드라마"),
    "데뷔못하면": ("데뷔 못 하면 죽는 병 걸림","female","드라마"),
    "악역의엔딩은죽음뿐": ("악역의 엔딩은 죽음뿐","female","로판"),
    "외과의사엘리제": ("외과의사 엘리제","female","로판"),
    "황제의외동딸": ("황제의 외동딸","female","로판"),
    "버림받은황비": ("버림받은 황비","female","로판"),
    "왕의딸로태어났다고": ("왕의 딸로 태어났다고 합니다","female","로판"),
    "재혼황후": ("재혼황후","female","로판"),
    "이번생은가주가": ("이번 생은 가주가 되겠습니다","female","로판"),
    "괴담출근": ("괴담에 떨어져도 출근을 해야 하는구나","all","드라마"),
    "무빙": ("무빙","all","액션"),
    "시맨틱에러": ("시맨틱 에러","female","BL"),
    "안경벗기면미인": ("안경 벗기면 미인","female","BL"),
    "상수리나무아래": ("상수리나무 아래","female","로판"),
    "왕세자입학도서": ("왕세자 입학도서","female","BL"),
    "피라미드게임": ("피라미드 게임","female","스릴러"),
    "정년이": ("정년이","female","드라마"),
    "비포선라이즈": ("비포 선라이즈","female","BL"),
    "신의탑": ("신의 탑","male","판타지"),
    "달빛조각사": ("달빛조각사","male","판타지"),
    "중증외상센터": ("중증외상센터","male","드라마"),
    "백작가의망나니": ("백작가의 망나니가 되었다","male","판타지"),
    "재벌집막내아들": ("재벌집 막내아들","male","드라마"),
    "전지적짝사랑": ("전지적 짝사랑 시점","female","로맨스"),
    "그녀가공작저로가야했던사정": ("그녀가 공작저로 가야 했던 사정","female","로판"),
    "버려진황비": ("버려진 황비","female","로판"),
    "역대급영지설계사": ("역대급 영지 설계사","male","판타지"),
    # LLM 분류로 확보한 실제 작품 (주간 휴리스틱 수집 정확도 향상)
    "열혈강호": ("열혈강호","male","무협"),
    "금지소년": ("금지소년","male","액션"),
    "벨제바브": ("벨제바브","male","액션"),
    "프리징": ("프리징","male","액션"),
    "검명무명": ("검명무명","male","무협"),
    "천생연분": ("천생연분","all","로맨스"),
    "불멸자": ("불멸자","male","판타지"),
    "은동스": ("은동스","all","일상"),
    "신의선물": ("신의 선물","female","로판"),
    "망나니pd아이돌로살아남기": ("망나니 PD 아이돌로 살아남기","all","드라마"),
    "잊혀진들판": ("잊혀진 들판","female","로맨스"),
    "천재대장장이": ("천재 대장장이의 게임","male","판타지"),
    "흑표가문의설표아기님": ("흑표가문의 설표 아기님","female","로판"),
    "검은머리미군대원수": ("검은 머리 미군 대원수","male","판타지"),
    "네가있던미래에선": ("네가 있던 미래에선","female","로판"),
    "터치유어바디": ("터치 유어 바디","female","BL"),
    "안개를삼킨나비": ("안개를 삼킨 나비","female","로판"),
    "순경씨와나": ("순경 씨와 나","all","드라마"),
    "이세계착각헌터": ("이세계 착각 헌터","male","판타지"),
    "이착헌": ("이세계 착각 헌터","male","판타지"),
    "오월의정원에서": ("오월의 정원에서","female","로판"),
    "꽃은미끼야": ("꽃은 미끼야","female","로맨스"),
    "헌터는조용히살고싶다": ("헌터는 조용히 살고 싶다","female","BL"),
    "코드네임아나스타샤": ("코드네임 아나스타샤","female","BL"),
    "디자이어미이프유캔": ("디자이어 미 이프 유 캔","female","BL"),
    "벨푸페의슈퍼달링": ("벨 푸페의 슈퍼달링 약혼","female","로판"),
    "우리흑마도사가너무귀여워": ("우리 흑마도사가 너무 귀여워!","female","로판"),
    "해피투게더": ("해피투게더","female","BL"),
    "악역영애안의사람": ("악역 영애 안의 사람","female","로판"),
    "피자배달부와골드팰리스": ("피자배달부와 골드팰리스","female","BL"),
    "피달부": ("피자배달부와 골드팰리스","female","BL"),
    "이딴게우렁각시": ("이딴 게 우렁각시?!","female","로맨스"),
    "백조무덤": ("백조 무덤","female","로판"),
    "취사병전설이되다": ("취사병 전설이 되다","male","일상"),
}
def match_known(text):
    norm = re.sub(r"\s+", "", text)
    for key, (title, g, genre) in KNOWN_WORKS.items():
        if key in norm:
            return title, g, genre
    return None

# 브랜드/뉴스(K-pop·엔터) 광고 신호 — 작품 광고와 분리
KW_BRAND = ["앨범","컴백","팬미팅","데뷔","투어","콘서트","빌보드","오리콘","차트","멤버",
            "아이돌","뮤직","MD","굿즈","발매","타이틀곡","뮤직비디오","엠넷","쇼케이스","월드투어","팬덤"]
BRAND_ADVERTISERS = ["entertainment","kakaoent","kakao.entertainment","sment","hybe","jyp","ygentertainment"]
def classify_ad_kind(advertiser, text, is_known_work):
    if is_known_work:
        return "작품"
    adv = (advertiser or "").lower()
    if any(b in adv for b in BRAND_ADVERTISERS):
        return "브랜드·뉴스"
    if sum(text.count(k) for k in KW_BRAND) >= 2:
        return "브랜드·뉴스"
    return "작품"

def classify_gender(text):
    f = sum(text.count(k) for k in KW_FEMALE)
    m = sum(text.count(k) for k in KW_MALE)
    if f == 0 and m == 0: return "all"
    return "female" if f >= m else "male"

def classify_genre(text):
    for genre, kws in GENRE_RULES:
        if any(k in text for k in kws):
            return genre
    return "기타"

BRAND_BLACKLIST = ["카카오페이지","kakaopage","kakao","카카오","리디","ridi","ridibooks","리디북스",
                   "네이버웹툰","webtoon","웹툰","line","kakaoent","entertainment","무료","웹소설","웹툰화"]
def _is_brand(s):
    sl = s.lower()
    return any(b in sl for b in [x.lower() for x in BRAND_BLACKLIST])

GENRE_WORDS = {"웹툰","웹소설","웹툰추천","애니","애니추천","리뷰","웹툰리뷰","개그","일상","로맨스","로판",
               "판타지","액션","무협","스릴러","드라마","BL","사이코패스","현판","순정","군대","군대썰","kakaopage"}
def extract_title(text):
    # '제목 : XXX' / '정보 : XXX (네이버웹툰)' 패턴 최우선
    for pat in [r"제목\s*[:：]\s*([^\n#(]{2,30})",
                r"정보\s*[:：]\s*([^\n#(]{2,30})"]:
        m = re.search(pat, text)
        if m:
            cand = m.group(1).strip().rstrip("(").strip()
            if cand and not _is_brand(cand): return cand
    # 괄호류 제목
    for pat in [r"[<《〈]([^<>《》〈〉]{2,30})[>》〉]",
                r"[「『]([^」』]{2,30})[」』]"]:
        for m in re.finditer(pat, text):
            cand = m.group(1).strip()
            if cand and not _is_brand(cand): return cand
    # 해시태그 중 브랜드어·장르어 아닌 첫 번째
    for m in re.finditer(r"#([^\s#]{2,20})", text):
        cand = m.group(1).strip()
        if cand and not _is_brand(cand) and cand not in GENRE_WORDS: return cand
    # 폴백: 첫 구절 앞부분 (이모지·구두점·체크표시 전까지)
    clean = re.split(r"[.!?\n。…💥🎊🔥✨▶➡👉|·✓✔]", text.strip(), 1)[0].strip()
    clean = re.sub(r"^[\s\"'·\-_✓✔🎊🎉💥]+", "", clean).strip()
    if 2 <= len(clean) <= 24 and not _is_brand(clean):
        return clean
    return None  # 추출 실패 → '(미상)'

# ---- Meta 광고 라이브러리 카드 추출 (js) --------------------------------
EXTRACT_JS = r"""
(() => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const idNodes = []; let n;
  while (n = walker.nextNode()) { if (/라이브러리 ID:\s*\d+/.test(n.nodeValue)) idNodes.push(n); }
  const cards = []; const seen = new Set();
  for (const tn of idNodes) {
    let el = tn.parentElement, card = null;
    for (let i=0;i<12 && el;i++){
      if (el.querySelector && el.querySelector('img[src*="scontent"]')) { card = el; break; }
      el = el.parentElement;
    }
    if (!card) continue;
    const txt = (card.innerText||"").replace(/\s+/g,' ');
    const idm = txt.match(/라이브러리 ID:\s*(\d+)/);
    if (!idm || seen.has(idm[1])) continue; seen.add(idm[1]);
    // 소재 형식 판별: 영상(video 태그) > 캐루셀(실제 크리에이티브 이미지 2장+) > 단컷
    const video = card.querySelector('video');
    // 실제 크리에이티브 이미지: 프로필(t51.2885-19) 제외 + 작은 아이콘(가로/세로<150) 제외
    const realImgs = [...card.querySelectorAll('img[src*="scontent"]')]
      .filter(im => !im.src.includes('t51.2885-19') && im.naturalWidth>=150 && im.naturalHeight>=150)
      .sort((a,b)=> (b.naturalWidth*b.naturalHeight) - (a.naturalWidth*a.naturalHeight));
    let format, images;
    if (video) {
      format = '영상';
      images = video.poster ? [video.poster] : [];
    } else if (realImgs.length >= 2) {
      format = '캐루셀';
      images = realImgs.slice(0, 8).map(im => im.src);
    } else {
      format = '단컷';
      images = realImgs.length ? [realImgs[0].src] : [];
    }
    const datem = txt.match(/(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.[^a-zA-Z]*?게재 시작/);
    const advm = txt.match(/(?:광고 상세 정보 보기|세부 사항 보기)\s+([^\s]+)\s+광고/);
    // 실제 카피 = 광고주명 + ' 광고 ' 뒤부터 (UI 잡음 제거)
    let copym = txt.match(/(?:상세 정보 보기|세부 사항 보기)\s+\S+\s+광고\s+(.{5,220})/);
    if(!copym) copym = txt.match(/광고\s+(.{8,200})/);
    cards.push({
      libId: idm[1],
      startDate: datem ? datem[1]+'-'+String(datem[2]).padStart(2,'0')+'-'+String(datem[3]).padStart(2,'0') : null,
      advertiser: advm ? advm[1] : null,
      format: format,
      images: images,
      copy: copym ? copym[1].trim() : txt.slice(0,160)
    });
  }
  return cards;
})()
"""

def card_count():
    return js("document.body.innerText.split('라이브러리 ID:').length - 1") or 0

def scroll_load(max_rounds=22):
    # 카드 수가 3회 연속 안정될 때까지 스크롤 (Meta lazy-load 변동 최소화)
    stable = 0; prev = -1
    for i in range(max_rounds):
        js("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2.4)
        cur = card_count()
        if cur <= prev: stable += 1
        else: stable = 0
        prev = max(prev, cur)
        if stable >= 3:
            break

def expand_grouped(max_rounds=15):
    # Meta는 동일 크리에이티브+문구가 여러 광고에 재사용되면 "N개에서 이 크리에이티브 및 문구를
    # 사용합니다" 카드 1장으로 묶어서 보여줌 -> "요약 세부 사항 보기" 클릭해야 나머지가 실제로 펼쳐짐.
    # 안 펼치면 활성 소재수가 실제보다 크게 적게 집계됨(실측: 네이버웹툰 10건 -> 펼친 후 19건).
    EXPAND_JS = r"""
    (() => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const idNodes = []; let n;
      while (n = walker.nextNode()) { if (/라이브러리 ID:\s*\d+/.test(n.nodeValue)) idNodes.push(n); }
      const seenCards = new Set();
      for (const tn of idNodes) {
        let el = tn.parentElement, card = null;
        for (let i=0;i<12 && el;i++){
          if (el.querySelector && el.querySelector('img[src*="scontent"]')) { card = el; break; }
          el = el.parentElement;
        }
        if (!card || seenCards.has(card)) continue; seenCards.add(card);
        const txt = card.innerText||"";
        if (/개에서 이 크리에이티브/.test(txt) && !card.dataset.expanded) {
          const btn = [...card.querySelectorAll('div[role="button"]')].find(x=>(x.innerText||'').includes('요약 세부 사항 보기'));
          if (btn) { card.dataset.expanded = '1'; btn.click(); return true; }
        }
      }
      return false;
    })()
    """
    for _ in range(max_rounds):
        clicked = js(EXPAND_JS)
        if not clicked:
            break
        time.sleep(1.8)
        try: js("window.scrollTo(0, document.body.scrollHeight)")
        except Exception: pass
        time.sleep(1.3)

def safe_newtab(url, tries=3):
    for i in range(tries):
        try:
            ensure_real_tab()
            new_tab(url); wait_for_load(); return True
        except Exception as e:
            print(f"    new_tab 재시도 {i+1}: {e}"); time.sleep(2)
    return False

def collect_target(t):
    from urllib.parse import quote
    page_mode = bool(t.get("page_id"))
    if page_mode:
        url = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
               "&country=KR&view_all_page_id=" + t["page_id"] + "&media_type=all")
        label = f"{t['competitor']}/page:{t['page_id']}"
    else:
        url = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
               "&country=KR&q=" + quote(t["q"]) + "&search_type=keyword_unordered&media_type=all")
        label = f"{t['competitor']}/{t['q']}"
    if not safe_newtab(url):
        print(f"  [{label}] 네비게이션 실패 — 스킵"); return []
    time.sleep(3)
    scroll_load(6)
    expand_grouped()
    scroll_load(6)  # 펼치기로 늘어난 카드까지 다시 안정화
    cards = js(EXTRACT_JS) or []
    kept = []
    for c in cards:
        if page_mode:
            pass  # 특정 페이지 전체 → 노이즈 없음
        else:
            adv = (c.get("advertiser") or "").lower()
            if not any(tok.lower() in adv for tok in t["advertiser_tokens"]):
                continue  # 제3자 노이즈 제거
            if not c.get("advertiser"): c["advertiser"] = t["competitor"]
        c["competitor"] = t["competitor"]
        c["category"] = t.get("category","웹툰")
        if page_mode and not c.get("advertiser"): c["advertiser"] = t["competitor"]
        kept.append(c)
    print(f"  [{label}] 카드 {len(cards)} → 통과 {len(kept)}")
    return kept

def download_img(url, fn):
    if not url: return None
    if os.path.exists(os.path.join(ASSETS, fn)):   # 캐시: 이미 받은 이미지는 스킵
        return "assets/" + fn
    try:
        b64 = js("""(async()=>{const r=await fetch(%s);const b=await r.blob();
          return await new Promise(res=>{const fr=new FileReader();fr.onloadend=()=>res(fr.result.split(',')[1]);fr.readAsDataURL(b);});})()"""
          % json.dumps(url))
        if not b64: return None
        with open(os.path.join(ASSETS, fn), "wb") as f:
            f.write(base64.b64decode(b64))
        return "assets/" + fn
    except Exception as e:
        print("    이미지 실패", fn, e); return None

def download_images(urls, libId):
    """캐루셀은 여러 장(최대 8), 단컷·영상은 1장. 인덱스 붙여 저장."""
    paths = []
    for i, url in enumerate(urls or []):
        fn = f"meta_{libId}.jpg" if i == 0 else f"meta_{libId}_{i}.jpg"
        p = download_img(url, fn)
        if p: paths.append(p)
    return paths

def days_between(a, b):
    from datetime import date
    ya,ma,da = map(int,a.split('-')); yb,mb,db = map(int,b.split('-'))
    return (date(yb,mb,db) - date(ya,ma,da)).days

# ================= 실행 =================
print("=== 수집 시작 ===", TODAY)
raw = {}
for t in TARGETS:
    for c in collect_target(t):
        raw[c["libId"]] = c   # libId dedupe (카루셀=1광고)

print(f"고유 광고(libId) {len(raw)}건 → 이미지 다운로드 + 분류")
records = []
OTT_BRAND = ["디즈니","disney","disneyplus","disneypluskr","tving","티빙","웨이브","wavve","넷플릭스","netflix",
             "쿠팡플레이","쿠팡 플레이","coupang","coupangplay","픽사","마블","스타워즈","내셔널지오그래픽","훌루","hulu","광고"]
OTT_JUNK = ["고화질","완결","단행본","할인","무료","광고형","스탠다드","이용권","웹 결제","독점","오리지널","구독","스트리밍"]
def _ott_brand(s):
    sl=s.lower().replace(" ","")
    return any(b.lower().replace(" ","") in sl for b in OTT_BRAND)
def extract_ott_title(text):
    for pat in [r"\[([^\[\]]{2,30})\]", r"[<《〈]([^<>《》〈〉]{2,30})[>》〉]", r"[「『]([^」』]{2,30})[」』]"]:
        for m in re.finditer(pat, text):
            cand=m.group(1).strip()
            if cand and not any(j in cand for j in OTT_JUNK) and not _ott_brand(cand):
                return cand
    for m in re.finditer(r"#([^\s#]{2,20})", text):
        cand=m.group(1).strip()
        if cand and not _ott_brand(cand): return cand
    return None

def ott_genre(text):
    if any(k in text for k in ["예능","버라이어티","관찰","코미디","쇼 ","리얼리티"]): return "예능"
    if any(k in text for k in ["영화","무비","극장"]): return "영화"
    if any(k in text for k in ["다큐","다큐멘터리"]): return "다큐"
    if any(k in text for k in ["애니메이션","애니 "]): return "애니"
    if any(k in text for k in ["스포츠","축구","야구","리그","경기"]): return "스포츠"
    return "드라마"

for libId, c in raw.items():
    copy = c.get("copy") or ""
    category = c.get("category","웹툰")
    if category == "OTT":
        title = extract_ott_title(copy) or "(브랜드 프로모션)"
        gender, genre = "all", ott_genre(copy)
        title_conf = "추정"; ad_kind = "콘텐츠"
    else:
        known = match_known(copy)
        if known:
            title, gender, genre = known; title_conf = "정확"
        else:
            title = extract_title(copy) or "(미상)"
            gender, genre = classify_gender(copy), classify_genre(copy); title_conf = "추정"
        ad_kind = classify_ad_kind(c.get("advertiser"), copy, bool(known))
        if ad_kind == "브랜드·뉴스":
            genre = "브랜드·뉴스"
            if title == "(미상)": title = "브랜드·뉴스 광고"
    fmt = c.get("format") or "단컷"
    img_paths = download_images(c.get("images"), libId)
    img_path = img_paths[0] if img_paths else None
    start = c.get("startDate") or TODAY
    dur = max(1, days_between(start, TODAY) + 1)
    records.append({
        "id": "meta_" + libId, "competitor": c["competitor"], "category": category, "media": "meta",
        "work_title": title, "gender": gender, "genre": genre, "title_conf": title_conf,
        "ad_kind": ad_kind,
        "type": "video" if fmt == "영상" else "image", "format": fmt,
        "image": img_path, "images": img_paths, "copy": copy[:140],
        "advertiser": c.get("advertiser"), "libId": libId,
        "first_seen": start, "last_seen": TODAY, "duration_days": dur, "active": True,
        "source": "meta", "confidence": "정확"  # 메타데이터는 정확, 분류(성향/장르/제목)는 추정
    })
print(f"레코드 {len(records)}건 생성")

# ---- history 스냅샷 (WoW) ----
snap = {"date": TODAY, "byCompetitor": {}}
for r in records:
    snap["byCompetitor"][r["competitor"]] = snap["byCompetitor"].get(r["competitor"], 0) + 1
with open(os.path.join(HISTORY, f"{TODAY}.json"), "w", encoding="utf-8") as f:
    json.dump(snap, f, ensure_ascii=False, indent=2)

# 과거 스냅샷 → weeklyTrend 구성
snaps = sorted([fn for fn in os.listdir(HISTORY) if fn.endswith(".json")])
trend = []
for fn in snaps[-6:]:
    s = json.load(open(os.path.join(HISTORY, fn), encoding="utf-8"))
    row = {"week": s["date"][5:]}
    for comp in ["네이버웹툰","카카오페이지","리디"]:
        row[comp] = s["byCompetitor"].get(comp, 0)
    trend.append(row)

# ---- data.js 생성 ----
webtoon_comps = sorted({r["competitor"] for r in records if r.get("category","웹툰")=="웹툰" and r["competitor"]!="네이버웹툰"})
ott_platforms = sorted({r["competitor"] for r in records if r.get("category")=="OTT"})
data = {
    "meta": {
        "lastUpdated": TODAY + " 09:00",
        "nextUpdate": "(주 1회 자동)",
        "weekLabel": TODAY,
        "owner": "네이버웹툰",
        "competitors": webtoon_comps or ["카카오페이지","리디"],
        "ottPlatforms": ott_platforms,
        "sources": {
            "meta":   {"label":"Meta (페북·인스타)","confidence":"정확","note":"Ad Library 실수집"},
            "google": {"label":"Google","confidence":"추정","note":"Transparency Center (수집 예정)"},
            "tiktok": {"label":"TikTok","confidence":"추정","note":"Creative Center (수집 예정)"},
            "kakao":  {"label":"Kakao","confidence":"수동","note":"공식 라이브러리 없음"}
        },
        "dataMode": "real",
        "collectorNote": "Meta 실데이터 자동 수집. 성향·장르·작품명은 카피 기반 휴리스틱(추정)."
    },
    "weeklyTrend": trend if len(trend) >= 2 else [
        {"week": TODAY[5:], **{c: sum(1 for r in records if r["competitor"]==c) for c in ["네이버웹툰","카카오페이지","리디"]}}
    ],
    "dateRange": {"min": min([r["first_seen"] for r in records] + [TODAY]), "max": TODAY},
    "creatives": records
}

out = "/* AUTO-GENERATED by collector/run_collect.py — 직접 수정 금지 */\nwindow.AD_DATA = " \
      + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
with open(os.path.join(BASE, "data.js"), "w", encoding="utf-8") as f:
    f.write(out)

print(f"=== 완료 === data.js 갱신 · 레코드 {len(records)} · 웹툰 {webtoon_comps} · OTT {ott_platforms}")
print(json.dumps({"records": len(records), "byComp": snap["byCompetitor"]}, ensure_ascii=False))
