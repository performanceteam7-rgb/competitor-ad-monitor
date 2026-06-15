# 경쟁사 광고 소재 모니터링 대시보드 — 설계

- 작성일: 2026-06-11
- 소유: 네이버웹툰 (관점: "우리=네이버웹툰", 경쟁사=카카오페이지·리디)
- 단계: **목업 + 더미데이터로 구조 확정** (자동화는 자리만)

## 목적
카카오페이지·리디가 구글·메타·틱톡·카카오에 집행하는 **광고 소재**를 모니터링.
- 광고되는 작품 수 / 소재 수
- 작품 성향(여성향·남성향·전체) + 주요 장르
- 실제 노출 광고 이미지(목업) + 노출기간
- 네이버웹툰 대비 인사이트
- 주 1회 자동 업데이트(추후)

## 데이터 모델 (creative 1건 = 1 레코드)
competitor / media / work_title / gender_orientation(female|male|all) /
genre / creative_type(image|video) / image(목업 썸네일) / copy_text /
first_seen / last_seen / duration_days / active / data_source / confidence(정확|추정|수동)

출처별 신뢰도: Meta=API(정확), Google=스크래핑(추정), TikTok=부분(추정), Kakao=수동(공식 라이브러리 없음).

## 화면 (한 페이지 스크롤)
1. 헤더·갱신 바 (갱신일/다음 갱신/신뢰도 범례)
2. KPI 카드 (경쟁사별 활성 소재·작품 수·이번주 신규·WoW)
3. 물량·점유율 (매체별 스택막대 + 주차 추세 라인)
4. 성향·장르 포커싱 (성별 도넛 + 장르 막대, vs 네이버웹툰)
5. 광고 이미지 갤러리 (필터: 경쟁사·매체·성향·장르·활성 / 정렬)
6. 노출기간 타임라인 (간트)
7. 인사이트 카드 4종 (데이터 기반 자동 생성)
8. 주간 변경 요약 (신규/종료/비중 변화)

## 데이터 흐름
- 지금: `index.html`(자체 완결, SVG 자체 차트=네트워크 무의존) + `data.js`(전역 `window.AD_DATA`, file:// 더블클릭 동작).
- 나중: Python 수집기가 `data.js`만 재생성 → 화면 무수정.
  - Meta=Ad Library API · Google=Transparency Center 스크래핑(browser-harness) · TikTok=Creative Center(부분) · Kakao=수동 입력
  - 매주 1회 cron(작업 스케줄러/GitHub Actions) + 주차 스냅샷 누적(WoW용)

## 비범위(이번)
실제 수집 자동화, 로그인/인증, 디자인 고도화 → 다음 단계.
