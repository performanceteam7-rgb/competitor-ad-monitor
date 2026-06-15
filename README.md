# 경쟁사 광고 소재 모니터링 대시보드

네이버웹툰 관점 · 카카오페이지/리디 광고 소재 모니터링. **Meta 광고 라이브러리 실데이터 자동 수집.**

## 🔗 공개 URL (외부 공유 가능)
**https://competitor-ad-monitor.vercel.app** — 로그인 없이 누구나 열람 가능.

로컬에서 보려면: `index.html` 더블클릭, 또는 `node server.js` → http://localhost:8848

## ✏️ 내 버전으로 수정/배포하기 (누구나)
이 저장소는 공개입니다. 누구나 받아서 자기 Claude Code/에디터에서 수정하고, 자기 Vercel로 배포할 수 있습니다.

```bash
# 1) 내려받기
git clone https://github.com/performanceteam7-rgb/competitor-ad-monitor.git
cd competitor-ad-monitor

# 2) 바로 보기 (설치 불필요)
node server.js          # → http://localhost:8848  (또는 index.html 더블클릭)

# 3) 내 Vercel로 배포
npx vercel --prod
```

- **Claude Code로 수정**: 위 폴더를 Claude Code로 열고 "○○ 바꿔줘"라고 요청하면 됩니다.
- **화면만 고치기**: `index.html`(UI·차트) / `data.js`(데이터)만 만지면 됩니다.
- **데이터 자동수집까지**: `collector/run_collect.py` 흐름 참고 (Windows + Chrome 필요).
- 수집과 화면이 분리돼 있어 `data.js`만 교체하면 화면은 그대로 동작합니다.

## 파일 구조
| 경로 | 역할 |
|------|------|
| `index.html` | 대시보드 화면 (SVG 자체 차트, 네트워크 무의존) |
| `data.js` | 데이터(`window.AD_DATA`). **수집기가 자동 재생성** — 직접 수정 금지 |
| `assets/meta_*.jpg` | 수집된 실제 광고 이미지 |
| `collector/run_collect.py` | Meta 광고 라이브러리 수집기 (browser-harness 실행) |
| `collector/run_weekly.ps1` | 주간 자동화: 수집 → 재배포 |
| `collector/history/` | 주차별 스냅샷 (WoW 추세용) |
| `server.js` | 로컬 미리보기 서버 |
| `vercel.json`, `.vercelignore` | 배포 설정 (collector·python 제외) |

## 담긴 요소 (8섹션)
헤더·갱신바 / KPI(사업자별 소재·작품 수·신규·WoW) / 매체별 물량·점유율 + 주차추세 /
성별성향 도넛 + 장르 포커싱 / 광고 이미지 갤러리(필터·정렬·검색) / 노출기간 타임라인 /
인사이트 4종(자동 생성) / 주간 변경 요약.

## 데이터 정확도
- **메타데이터(이미지·게재일·라이브러리 ID·노출기간)** = 정확 (Meta 라이브러리 원본)
- **성향·장르·작품명** = 추정 (광고 카피 휴리스틱 분류) → 카드에 `●추정` 표기
- **네이버웹툰(자사)** = Meta 공개 라이브러리에 안 잡힘 → **자사 광고계정 연동 필요** (대시보드에 경고 표시)

## 수동 실행
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:BH_TODAY=(Get-Date -Format "yyyy-MM-dd")
cmd /c "C:\Users\MADUP\.local\bin\browser-harness.exe < C:\Users\MADUP\competitor-ad-monitor\collector\run_collect.py"
npx vercel --prod --yes   # 재배포
```

## 주 1회 자동 갱신 (등록됨)
- 작업 스케줄러 태스크 **`CompetitorAdMonitor-Weekly`** — 매주 월요일 09:00
- 동작: `collector/run_weekly.ps1` → Meta 수집 → `data.js` 갱신 → Vercel 재배포 → `collector/logs/`에 기록
- 전제: 사용자 Chrome 실행 중(Meta 라이브러리는 로그인 불필요), Vercel CLI 로그인 1회 완료(토큰 저장됨)
- 해제: `Unregister-ScheduledTask -TaskName CompetitorAdMonitor-Weekly`

## 알려진 한계 / 다음 단계
- 키워드 검색은 광고주 화이트리스트로 제3자 노이즈 제거. kakao.entertainment(K-pop 뉴스)는 웹툰 외 광고도 포함됨 → 광고주별 분리 정밀화 여지.
- 작품명/장르 추출은 휴리스틱 → LLM 분류로 정확도 향상 가능.
- Google Transparency Center / TikTok Creative Center 수집기 추가 예정. Kakao는 공식 라이브러리 없어 수동.
- 자사(네이버웹툰) 데이터: Meta Business 광고계정 API 연동 시 "vs 네이버웹툰" 비교 활성화.
