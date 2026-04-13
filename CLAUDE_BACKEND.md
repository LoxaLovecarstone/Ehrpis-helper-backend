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
- httpx, beautifulsoup4, firebase-admin, python-dotenv
- GitHub Actions (스케줄러)
- Firebase Firestore (쿠폰 저장)
- FCM (푸시 알림)
- jsDelivr CDN (캐릭터 JSON 서빙)

## 폴더 구조
```
Ehrpis-helper-backend/
├── .github/
│   └── workflows/
│       └── crawl.yml         ← 스케줄러 (한국시간 10:00~11:30, 30분 간격)
├── crawler/
│   ├── __init__.py
│   ├── coupon_crawler.py     ← 네이버 라운지 크롤링
│   └── firebase_client.py   ← Firestore 저장 + FCM 발송
├── data/
│   ├── common/
│   │   ├── classes.json      ← 직업 (수호/돌격/언령/사수)
│   │   ├── elements.json     ← 속성 (수/화/목/암/광)
│   │   ├── roles.json        ← 역할 (딜러/탱커/힐러/서포터)
│   │   ├── badges.json       ← 뱃지 10종
│   │   ├── element_relations.json
│   │   └── fever_config.json
│   └── characters/
│       ├── index.json        ← 캐릭터 목록 (경량)
│       ├── 638318.json       ← 고스트 사무라이 (완성)
│       ├── 693404.json       ← 조무 (스킬 미완성)
│       ├── 638300.json       ← 아스트레아 (스킬 미완성)
│       └── 675887.json       ← 영요 (스킬 미완성)
├── .gitignore                ← serviceAccountKey.json 포함
├── main.py                   ← 진입점
└── requirements.txt
```

## 크롤러 동작 방식

### 네이버 라운지 API
```
목록: GET https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed
      ?boardId=25&buffFilteringYN=N&limit=25&offset=0&order=NEW

상세: GET https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed/{feed_id}
```

### 쿠폰 감지 조건
- `feed.title`에 `[리딤]` 포함
- 본문 HTML에서 `코드명: [XXXXX]` 패턴으로 쿠폰 코드 추출

### 중복 방지
Firestore에 `feed_id` 기준으로 저장. 이미 존재하면 스킵 후 `break`.

## Firestore 구조

### coupons 컬렉션
```
feed_id: int
title: string
coupons: array[string]
expiry_start: string  ("2026-04-06")
expiry_end: string    ("2026-04-08 23:59")
link: string
created_date: string  ("20260406111025")
notified: bool
```

### tier_votes 컬렉션
```
character_id: int
content_type: string  ("PVP" or "PVE")
tier: string          ("S"/"1"/"2"/"3"/"4"/"5")
user_fingerprint: string
created_at: timestamp
```

### tier_summary 컬렉션
도큐먼트 ID: `{character_id}_{content_type}`
```
character_id: int
content_type: string
tier_S / tier_1 / tier_2 / tier_3 / tier_4 / tier_5: int
total_votes: int
top_tier: string
```

## FCM Payload 구조
```json
{
  "notification": {
    "title": "🎫 새 쿠폰 도착!",
    "body": "GIFTS0406 | 2026-04-08 23:59까지"
  },
  "data": {
    "route": "coupon_list",
    "feed_id": "7508947",
    "coupons": "GIFTS0406",
    "expiry_end": "2026-04-08 23:59",
    "link": "https://game.naver.com/lounge/Ehrpis/board/detail/7508947"
  },
  "topic": "coupons",
  "android": {
    "priority": "high",
    "notification": {
      "click_action": "OPEN_COUPON_LIST"
    }
  }
}
```

## GitHub Actions
```yaml
# crawl.yml 스케줄
- cron: '0 1 * * *'    # 한국시간 10:00
- cron: '30 1 * * *'   # 한국시간 10:30
- cron: '0 2 * * *'    # 한국시간 11:00
- cron: '30 2 * * *'   # 한국시간 11:30
```

GitHub Secrets에 `FIREBASE_KEY` 등록 필요.

## CDN URL 형태
```
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/characters/index.json
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/characters/638318.json
https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/data/common/classes.json
```

## 캐릭터 JSON 구조 핵심
```json
{
  "id": 638318,
  "name_ko": "고스트 사무라이",
  "name_en": "Ghostsamurai",
  "name_cn": "鬼侍",
  "rarity": 5,
  "class_id": 1,
  "element_id": 2,
  "role_id": 2,
  "stats": { "atk_max": 762, "hp_max": 17937, ... },
  "skills": [
    {
      "id": "638318_normal",
      "type": "normal/battle/fever",
      "hits": 1,
      "multipliers": [{ "stat": "atk", "base_type": "total/base", "ratio": 1.00 }],
      "effects": []
    }
  ],
  "passives": [...],
  "awakenings": [
    { "step": 1, "effect_type": "stat_bonus", "target_stat": "hp", "value_type": "flat", "value": 1002 }
  ],
  "badge_recommendation": "revival",
  "leader_skill": {
    "condition": "fever",
    "effects": [{ "effect_type": "stat_bonus", "target_stat": "atk_percent", "value": 0.05, "target": "ally_all" }]
  }
}
```

## 현재 상태
- 크롤러 완성, GitHub Actions 동작 확인
- Firestore 쿠폰 저장 + FCM 푸시 확인
- 캐릭터 JSON: 638318 (고스트 사무라이) 완성
- 나머지 3개 캐릭터 스킬/각성 데이터 미완성

## 다음 작업
- 나머지 캐릭터 데이터 완성 (gamekee 위키 참고: https://www.gamekee.com/xl/)
- 캐릭터 추가 시 index.json도 함께 업데이트
- tier_summary 갱신 로직 추가 고려
