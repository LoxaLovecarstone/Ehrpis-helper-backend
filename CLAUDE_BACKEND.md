# 에르피스 도우미 앱 - 백엔드

## 프로젝트 개요
에르피스(Ehrpis) 모바일 게임 도우미 앱 백엔드.
서버리스 구조: GitHub Actions + Firebase (Firestore + FCM)

## 레포 정보
- GitHub: `LoxaLovecarstone/Ehrpis-helper-backend`
- 브랜치 전략: `develop` → `feat/*` → PR → `main`
- GitHub Actions는 `main` 브랜치 기준으로 동작

## 기술 스택
- Python 3.13
- httpx, beautifulsoup4, firebase-admin, python-dotenv, emoji
- GitHub Actions (스케줄러)
- Firebase Firestore (쿠폰 저장)
- FCM (푸시 알림)
- jsDelivr CDN (캐릭터 JSON 서빙)

## 폴더 구조
```
Ehrpis-helper-backend/
├── .github/
│   └── workflows/
│       ├── crawl.yml             ← 쿠폰 크롤링 스케줄
│       └── cleanup.yml           ← 만료 쿠폰 삭제 스케줄
├── crawler/
│   ├── __init__.py
│   ├── coupon_crawler.py         ← 네이버 라운지 크롤링
│   └── firebase_client.py        ← Firestore 저장 + FCM 발송
├── data/
│   ├── common/
│   │   ├── classes.json          ← 직업 (수호/돌격/언령/사수)
│   │   ├── elements.json         ← 속성 (수/화/목/암/광)
│   │   ├── roles.json            ← 역할 (딜러/탱커/힐러/서포터)
│   │   ├── badges.json           ← 뱃지 10종
│   │   ├── element_relations.json
│   │   └── fever_config.json
│   └── characters/
│       ├── index.json            ← 캐릭터 목록 (경량, CDN 서빙)
│       ├── icons/                ← 0001.png ~ 0066.png (172×172 투명 PNG)
│       ├── 0001.json ~ 0066.json ← 개별 캐릭터 상세 (lazy load용 껍데기)
├── scripts/
│   └── cleanup_expired_coupons.py
├── main.py
└── requirements.txt
```

---

## 캐릭터 데이터 구조

### ID 체계
- 한국 서버 출시 캐릭터 **66명** 기준
- ID: 순번 정수 (1~66), 파일명은 4자리 zero-padding (`0001.png`, `0001.json`)
- content_id(GameKee 기반) 더 이상 사용하지 않음

### index.json 역할
앱이 jsDelivr CDN에서 받는 **경량 캐릭터 목록**.

- **가챠 시뮬레이터** — `is_gacha: true`인 캐릭터만 뽑기 풀에 넣고, `rarity`로 확률 계산
- **UI 표시** — `icon_url`로 아이콘, `name_ko`로 이름, `class_id`/`element_id`/`role_id`로 필터
- **픽업 배너** — `is_limited`로 한정 캐릭터 구분

### index.json 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | int | 순번 PK (1~66) |
| `name_ko` | string | 한국어 이름 |
| `name_en` | string | 영어 이름 |
| `rarity` | int | 성급 (1~5) |
| `class_id` | int | 직업 ID (classes.json 참조) |
| `element_id` | int | 속성 ID (elements.json 참조) |
| `role_id` | int | 역할 ID (roles.json 참조) |
| `is_limited` | bool | 한정 캐릭터 여부 |
| `is_gacha` | bool | 가챠 풀 포함 여부 (획득 경로가 가챠가 아닌 캐릭터는 false) |
| `icon_url` | string | jsDelivr CDN URL |

### 개별 캐릭터 JSON (0001.json ~ 0066.json)
캐릭터 상세 페이지 진입 시 lazy load. 현재는 확장용 껍데기.

```json
{
  "id": 1,
  "skills": [],
  "passives": [],
  "awakenings": [],
  "stats": {}
}
```

향후 추가 예정 필드: `badge_recommendation`, `leader_skill`

### 아이콘
- 위치: `data/characters/icons/0001.png` ~ `0066.png`
- 규격: 172×172px, 원형 투명 PNG (피그마 export)
- CDN URL: `https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/characters/icons/0001.png`

---

## 크롤러 동작 방식 (쿠폰)

### 네이버 라운지 API
```
목록: GET https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed
      ?boardId=25&buffFilteringYN=N&limit=25&offset=0&order=NEW

상세: GET https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed/{feed_id}
```

### 쿠폰 감지 조건
- `feed.title`에 `[리딤]` 포함
- 본문 HTML에서 쿠폰 코드 추출

### 중복 방지
Firestore에 `feed_id` 기준으로 저장. 이미 존재하면 스킵 후 `break`.

---

## Firestore 구조

### coupons 컬렉션
```
feed_id: int
title: string
coupons: array[string]
expiry_start: string  ("2026-04-06")
expiry_end: string    ("2026-04-08 23:59")
reward_types: array[string]
link: string
created_date: string  ("20260406111025")
notified: bool
```

---

## FCM Payload 구조
```json
{
  "data": {
    "title": "🎫 새 쿠폰 도착!",
    "body": "GIFTS0406 | 2026-04-08 23:59까지",
    "route": "coupon_list",
    "feed_id": "7508947",
    "coupons": "GIFTS0406",
    "expiry_end": "2026-04-08 23:59",
    "link": "https://game.naver.com/lounge/Ehrpis/board/detail/7508947"
  },
  "topic": "coupons",
  "android": {
    "priority": "high"
  }
}
```
`notification` 블록 없이 전부 `data`로만 전송. 앱에서 직접 알림 구성.

---

## CDN URL 형태
```
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/characters/index.json
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/characters/0001.json
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/characters/icons/0001.png
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/common/classes.json
```

## GitHub Actions
```yaml
# crawl.yml 스케줄 (KST 기준)
- cron: '7 1 * * *'    # 10:07
- cron: '37 1 * * *'   # 10:37
- cron: '7 2 * * *'    # 11:07
- cron: '37 2 * * *'   # 11:37
- cron: '7 8 * * *'    # 17:07

# cleanup.yml
- cron: '0 15 * * *'   # KST 00:00
```
