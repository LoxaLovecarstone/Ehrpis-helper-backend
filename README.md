# Ehrpis Helper — Backend

모바일 게임 `에르피스`를 도와주는 `에르피스 도우미` 앱의 백엔드입니다.

네이버 게임 라운지를 주기적으로 크롤링해 쿠폰 게시글을 감지하고, Firestore에 저장 후 FCM으로 푸시 알림을 발송합니다.

별도 서버 없이 **GitHub Actions + Firebase** 로 작동합니다.

---

## 아키텍처

```
[GitHub Actions 스케줄러]
        │  매일 5회 (KST 10:07 / 10:37 / 11:07 / 11:37 / 17:07)
        ▼
[coupon_crawler.py]
  네이버 라운지 API 목록 조회
        │  [리딤] 포함 게시글 필터
        ▼
  상세 API 조회 → 쿠폰 코드 추출 (정규식 이중 패턴)
                → 만료일 추출
                → 보상 타입 추출
        │
        ▼
[firebase_client.py]
  Firestore feed_id 중복 확인
        │  신규이면
        ├─▶ Firestore coupons 컬렉션 저장
        └─▶ FCM topic "coupons" 발송

[cleanup.yml]
  매일 KST 00:00 → 만료된 쿠폰 Hard Delete
```

---

## 기술 스택

| 영역 | 기술                             |
|---|--------------------------------|
| 언어 | Python 3.14                    |
| HTTP 클라이언트 | httpx (비동기)                    |
| HTML 파싱 | BeautifulSoup4                 |
| 데이터베이스 | Firebase Firestore             |
| 푸시 알림 | Firebase Cloud Messaging (FCM) |
| 스케줄러 | GitHub Actions                 |

---

## 폴더 구조

```
Ehrpis-helper-backend/
├── .github/
│   └── workflows/
│       ├── crawl.yml               ← 쿠폰 크롤링 스케줄 (매일 5회)
│       └── cleanup.yml             ← 만료 쿠폰 삭제 스케줄 (매일 KST 00:00)
├── crawler/
│   ├── coupon_crawler.py           ← 네이버 라운지 크롤링 + 파싱
│   └── firebase_client.py          ← Firestore 저장 + FCM 발송
├── scripts/
│   └── cleanup_expired_coupons.py  ← 만료 쿠폰 Hard Delete
├── main.py                         ← 진입점
└── requirements.txt
```

---

## 크롤링 동작 방식

### 1. 목록 조회

네이버 게임 라운지 공개 API를 페이지 단위로 순회합니다.

```
GET https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed
    ?boardId=25&buffFilteringYN=N&limit=25&offset={page}&order=NEW
```

`[리딤]`이 제목에 포함된 게시글만 추려 상세 조회로 넘깁니다.

### 2. 상세 조회 + 파싱

```
GET https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed/{feed_id}
```

본문 HTML에서 세 가지를 추출합니다.

**쿠폰 코드** — 정규식 이중 패턴:
```python
pattern1 = re.findall(r'코드명[^\w]*\[?([A-Z0-9]{4,20})\]?', text)   # "코드명: [GIFTS0406]"
pattern2 = re.findall(r'\b[A-Z][A-Z0-9]{5,19}\b', text)              # 대문자+숫자 조합
```
pattern1 우선 적용 후 중복을 제거합니다.

**만료일** — `보상 수령 기간 : 2026-04-06 ~ 2026-04-08 23:59` 패턴으로,
`YYYY-MM-DD` / `YYYY.MM.DD` 두 형태 모두 파싱합니다.

**보상 타입** — `오팔`, `운명의 그림자`, `기적의 그림자` 포함 여부로 분류합니다.

### 3. 중복 방지

Firestore에 `feed_id`가 이미 존재하면 스킵하고 루프를 종료합니다.
게시글이 최신순 정렬이므로 기존 게시글을 만나는 순간 이후는 모두 이전 데이터이기 때문입니다.

---

## Firestore 스키마

### `coupons` 컬렉션

도큐먼트 ID: `{feed_id}`

| 필드 | 타입 | 예시 |
|---|---|---|
| `feed_id` | int | `7508947` |
| `title` | string | `[리딤] 4월 보상 쿠폰` |
| `coupons` | array\<string\> | `["GIFTS0406"]` |
| `expiry_start` | string | `"2026-04-06"` |
| `expiry_end` | string | `"2026-04-08 23:59"` |
| `reward_types` | array\<string\> | `["오팔"]` |
| `link` | string | 게시글 URL |
| `created_date` | string | `"20260406111025"` |
| `notified` | bool | `false` |

---

## FCM 페이로드

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
    "notification": { "click_action": "OPEN_COUPON_LIST" }
  }
}
```

`notification`은 시스템 트레이 표시용, `data`는 앱 딥링크용으로 분리했습니다.

---

## GitHub Actions 스케줄

### crawl.yml — 쿠폰 크롤링

| cron | KST |
|---|---|
| `7 1 * * *` | 10:07 |
| `37 1 * * *` | 10:37 |
| `7 2 * * *` | 11:07 |
| `37 2 * * *` | 11:37 |
| `7 8 * * *` | 17:07 |

에르피스 공식 쿠폰 게시 시간대인 10시 ~ 11시의 정보를 크롤링하며, 하루의 마지막 시점에 한 번 더 체크합니다.

`workflow_dispatch`로 수동 실행도 가능합니다.

### cleanup.yml — 만료 쿠폰 삭제

매일 `15:00 UTC` (KST 00:00). `expiry_end` 기준으로 만료된 도큐먼트를 Firestore batch delete 합니다.
`soft delete`도 고려하였으나 어차피 만료된 쿠폰을 다시는 사용하지 못하는 점, 무료 요금제를 이용 중이라는 조건에 맞추어 타협하였습니다.

---

## 로컬 실행

```bash
pip install -r requirements.txt

# serviceAccountKey.json 을 프로젝트 루트에 배치 (Firebase 콘솔에서 발급)
python main.py
```

GitHub Actions 환경에서는 `FIREBASE_KEY` Secret에 서비스 계정 JSON을 통째로 등록합니다.
