# 에르피스 도우미 앱 - 백엔드

## 프로젝트 개요
에르피스(Ehrpis) 모바일 게임 도우미 앱 백엔드.
서버리스 구조: GitHub Actions + Firebase (Firestore + FCM)

## 레포 정보
- GitHub: `LoxaLovecarstone/Ehrpis-helper-backend`
- 브랜치 전략: `develop` → `feat/*` → PR → `main`
- GitHub Actions는 `main` 브랜치 기준으로 동작

## 기술 스택
- Python 3.14
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
│   ├── gacha/
│   │   ├── banner_config.json    ← 확률·천장 설정 (CDN 서빙)
│   │   ├── starlight_config.json ← 별빛 수치 설정 (CDN 서빙)
│   │   └── gacha_packages.json  ← 인앱 패키지 목록 (CDN 서빙)
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
| `role_ids` | array\<int\> | 역할 ID 목록 (roles.json 참조, 복수 허용) |
| `is_limited` | bool | 한정 캐릭터 여부 |
| `is_gacha` | bool | 가챠 풀 포함 여부 (획득 경로가 가챠가 아닌 캐릭터는 false) |
| `is_standard_pool` | bool | 상시 편입 여부. 한정(`is_limited:true`) 및 비가챠(`is_gacha:false`)는 false |
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
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/gacha/banner_config.json
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/gacha/starlight_config.json
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/gacha/gacha_packages.json
```

## 안드로이드 연동 시 참고사항

안드로이드 에이전트에 넘길 때 아래 내용 포함:

- CDN에서 index.json fetch → `is_gacha: true`인 캐릭터만 가챠 풀에 포함
- `is_limited`로 픽업 배너 구분
- `icon_url` 직접 사용 (172×172 원형 투명 PNG)
- `role_ids`는 배열 (복수 역할 허용)
- 직업/속성/역할 상세는 `data/common/*.json` 별도 fetch

---

## GitHub Actions
```yaml
# crawl.yml 스케줄 (KST 기준)
- cron: '30 23 * * *'  # 08:30 — 아침 폴링 루프 (11:20까지)
- cron: '30 6 * * *'   # 15:30 — 저녁 폴링 루프 (18:00까지)

# cleanup.yml
- cron: '0 15 * * *'   # KST 00:00
```

## 폴링 루프 구조 (main.py)

잡이 시작되면 5분 간격으로 반복 크롤링. 시작 시각 기준으로 deadline 자동 결정 (12시 전 → 11:20, 이후 → 18:00). 새 쿠폰 발견 시 Firestore 저장 + FCM 발송 후에도 계속 폴링 (하루 쿠폰 2개 이상 대비). feed_id dedup 로직이 중복 알림 차단.

```python
POLL_INTERVAL = 300  # 5분

now = datetime.datetime.now(KST)
if now.hour < 12:
    deadline = now.replace(hour=11, minute=20, ...)
else:
    deadline = now.replace(hour=18, minute=0, ...)

while True:
    await crawl_once()
    if datetime.datetime.now(KST) >= deadline:
        break
    await asyncio.sleep(POLL_INTERVAL)
```

## DEV_ONLY 환경변수

로컬 테스트 시 prod Firebase 격리용. CI에서는 설정하지 않음.

```powershell
$env:DEV_ONLY="true"; python main.py
$env:DEV_ONLY="true"; python scripts/test_send_dummy.py  # FCM 테스트
$env:DEV_ONLY="true"; python scripts/test_cleanup.py     # 테스트 데이터 정리
```

---

## GitHub Actions 딜레이 및 트리거 시각 고려사항

### 실측 딜레이 (32일, 224회)
- 아침 슬롯 (09:07 KST = 00:07 UTC): **39~78분** 지연
- 저녁 슬롯 (16:07 KST = 07:07 UTC): 최대 88분 지연

### 현재 구조의 한계
쿠폰은 보통 **10:00 / 11:00 KST**에 올라옴. 09:07 cron이 78분 지연되면 루프가 10:25에야 시작 → 10:00 쿠폰을 25분 후 인지. 사용자 입장에서 10분 이내 알림 보장 불가.

### 개선 후보 (미적용, 일주일 통계 후 결정)
- cron을 **08:00 KST (23:00 UTC)**로 당기기
  - 23:00 UTC는 자정 전이라 혼잡도 낮음
  - 최악 78분 지연 시 09:18 시작 → 10:00 쿠폰을 3분 이내 감지
  - deadline 11:30 유지로 11:00 쿠폰도 커버

### Firestore 읽기 비용
- 폴링 루프 기준 **~97 reads/일** (사이클당 1회, 첫 게시글이 이미 저장돼 있어 break)
- 현재 36명 기준 클라이언트 조회 약 300 reads/일
- 500명 기준 예상 ~4,264 reads/일 → 무료 한도(50,000/일) 내
- 게임 전체 유저 2,000명 미만이라 비용 이슈 없음

### 폴링 간격 변경 시 비교 (3분 vs 5분)

| 항목 | 3분 (현재) | 5분 |
|------|-----------|-----|
| 아침 사이클 수 | ~47회 | ~28회 |
| 저녁 사이클 수 | ~50회 | ~28회 |
| 서버 reads/일 | ~97회 | ~56회 |
| 쿠폰 최대 감지 지연 | 3분 | 5분 |

결론: reads 차이는 41회로 비용 관점에선 의미 없음. 쿠폰 감지 지연이 최대 2분 늘어나는 게 유일한 트레이드오프인데, cron 자체 딜레이(39~78분)가 지배적이라 체감 차이도 없음. **현재 3분 유지가 합리적**.
