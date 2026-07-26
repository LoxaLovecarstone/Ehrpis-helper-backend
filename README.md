# Ehrpis Helper — Backend

모바일 게임 `에르피스`를 도와주는 `에르피스 도우미` 앱의 백엔드입니다.

네이버 게임 라운지를 주기적으로 모니터링해 쿠폰 게시글을 감지하고, Firestore에 저장 후 FCM으로 푸시 알림을 발송합니다.
캐릭터 데이터 및 가챠 설정은 jsDelivr CDN을 통해 앱에 서빙합니다.

별도 서버 없이 **GitHub Actions + Firebase** 로 작동합니다.

---

## 아키텍처

```
[GitHub Actions 스케줄러]
        │  오전: 08:30 KST 시작 → 5분 간격 모니터링 → 11:20 종료
        │  오후: 15:30 KST 시작 → 5분 간격 모니터링 → 18:00 종료
        ▼
[coupon_crawler.py]
  네이버 라운지 API 목록 조회 (지원 코드 게시판, 최신순)
        │  이미 저장된 feed_id 만나면 즉시 중단
        ▼
  상세 API 조회 → 쿠폰 코드 추출 (정규식 이중 패턴)
        │        → 코드 없으면 스킵 (제목 헤더로는 필터링하지 않음)
        │        → 만료일 추출
        │        → 보상 타입 추출
        │
        ▼
[main.py]
  만료된 쿠폰 스킵
        │
  Firestore feed_id 중복 확인
        │  신규이면
        ├─▶ [firebase_client.py] Firestore coupons 컬렉션 저장
        └─▶ [firebase_client.py] FCM topic "coupons" 발송

[cleanup.yml]
  매일 KST 00:00 → 만료된 쿠폰 Hard Delete
```

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| 언어 | Python 3.14 |
| HTTP 클라이언트 | httpx (비동기) |
| HTML 파싱 | BeautifulSoup4 |
| 이모지 처리 | emoji |
| 데이터베이스 | Firebase Firestore |
| 푸시 알림 | Firebase Cloud Messaging (FCM) |
| 스케줄러 | GitHub Actions |
| CDN | jsDelivr (캐릭터 데이터 서빙) |

---

## 폴더 구조

```
Ehrpis-helper-backend/
├── .github/
│   └── workflows/
│       ├── crawl.yml               ← 쿠폰 크롤링 (08:30 / 15:30 KST 모니터링 루프)
│       └── cleanup.yml             ← 만료 쿠폰 삭제 스케줄 (매일 KST 00:00)
├── crawler/
│   ├── coupon_crawler.py           ← 네이버 라운지 크롤링 + 파싱
│   └── firebase_client.py          ← Firestore 저장 + FCM 발송
├── data/
│   ├── common/
│   │   ├── classes.json            ← 직업 (수호/돌격/언령/사수)
│   │   ├── elements.json           ← 속성 (수/화/목/광/암)
│   │   ├── roles.json              ← 역할 (딜러/탱커/힐러/서포터)
│   │   └── ...
│   ├── characters/
│   │   ├── index.json              ← 캐릭터 목록 (경량, CDN 서빙)
│   │   ├── icons/                  ← 0001.png ~ 0066.png (172×172 투명 PNG)
│   │   └── 0001.json ~ 0066.json  ← 개별 캐릭터 상세 (lazy load용)
│   └── gacha/
│       ├── banner_config.json      ← 확률·천장 설정 (CDN 서빙)
│       ├── starlight_config.json   ← 별빛 수치 설정 (CDN 서빙)
│       └── gacha_packages.json     ← 인앱 패키지 목록 (CDN 서빙)
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

이 게시판(`boardId=25`)은 애초에 "지원 코드" 전용 게시판이라 제목 헤더로는 따로 필터링하지 않고, 최신 게시글부터 순서대로 전부 상세 조회로 넘깁니다. 대신 이미 Firestore에 저장된 `feed_id`를 만나면(= 이전에 처리한 게시글에 도달하면) 그 시점에 순회를 멈춰 매 폴링마다 게시판 전체 이력을 다시 훑지 않습니다.

> 과거에는 제목에 `[리딤]`이 포함된 게시글만 걸렀지만, 운영자가 헤더 표기 없이 제목을 쓴 게시글(예: "고스트킹 합류 기념 특별 쿠폰")이 감지되지 않는 문제가 있어 제거했습니다. 지금은 아래 2단계에서 본문에 쿠폰 코드가 실제로 있는지로 판단합니다.

### 2. 상세 조회 + 파싱

```
GET https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed/{feed_id}
```

본문 HTML에서 세 가지를 추출합니다.

**쿠폰 코드** — 정규식 이중 패턴:
```python
text = soup.get_text(separator=' ')  # 태그 경계에 공백 삽입 (한글 \b 오작동 방지)

pattern1 = re.findall(r'(?:코드명|쿠폰\s*코드)[^\w]*\[?([A-Z0-9]{4,20})\]?', text)  # "코드명: [GIFTS0406]" / "쿠폰 코드 : MYHEART"
pattern2 = re.findall(r'\b[A-Z][A-Z0-9]{5,19}\b', text)                             # 대문자+숫자 조합 fallback
```
pattern1 우선 적용 후 중복을 제거합니다. 둘 다 매치되지 않아 코드가 하나도 없으면 쿠폰 게시글이 아닌 것으로 보고 스킵합니다(= 게시글 채택 여부 자체가 이 결과에 달려 있습니다).

> **주의:** `get_text()` 기본값은 태그 경계를 공백 없이 이어붙이기 때문에 한글 직후에 쿠폰 코드가 붙어 `\b`(word boundary)가 동작하지 않습니다. Python 3에서 한글은 `\w`로 분류되므로, `separator=' '`로 태그 경계마다 공백을 삽입해야 합니다.

**만료일** — `보상 수령 기간` 또는 `쿠폰 사용 기간` 뒤에 오는 날짜 범위를 추출합니다.
`2026-04-06 ~ 2026-04-08 23:59` 형태이며, `YYYY-MM-DD` / `YYYY.MM.DD` 두 형태 모두 파싱합니다.

**보상 타입** — `오팔`, `운명의 그림자`, `기적의 그림자` 포함 여부로 분류합니다.

### 3. 중복 방지

크롤링 시작 전 Firestore `active_coupons`에서 이미 저장된 `feed_id` 집합을 1회 읽어오고, 목록 조회 중 이 집합에 속한 `feed_id`를 만나는 즉시 순회를 종료합니다(1단계에 통합).
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
  "data": {
    "title": "🎫 새 쿠폰 도착!",
    "body": "GIFTS0406  |  2026-04-08 23:59까지",
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

`notification` 블록 없이 전부 `data`로만 전송합니다. 앱에서 `data`의 `title` / `body`를 읽어 직접 알림을 구성합니다.

---

## GitHub Actions 스케줄

### crawl.yml — 쿠폰 크롤링

| cron (UTC) | KST 시작 | deadline | 동작 |
|---|---|---|---|
| `30 23 * * *` | 08:30 | 11:20 | 5분 간격 모니터링 루프 |
| `30 6 * * *` | 15:30 | 18:00 | 5분 간격 모니터링 루프 |

GitHub Actions cron 딜레이(실측 평균 40~80분)를 우회하기 위해 모니터링 루프 방식을 채택했습니다. 잡이 뜨는 순간부터 5분 간격으로 반복 크롤링하며, 쿠폰 발견 즉시 저장 + FCM 발송합니다. deadline까지 쿠폰이 없으면 자동 종료합니다.

`workflow_dispatch`로 수동 실행도 가능합니다.

### cleanup.yml — 만료 쿠폰 삭제

매일 `15:00 UTC` (KST 00:00). `expiry_end` 기준으로 만료된 도큐먼트를 Firestore batch delete 합니다.
`soft delete`도 고려하였으나 어차피 만료된 쿠폰을 다시는 사용하지 못하는 점, 무료 요금제를 이용 중이라는 조건에 맞추어 타협하였습니다.

`workflow_dispatch`로 수동 실행도 가능합니다.

---

## CDN 서빙 (캐릭터 데이터)

캐릭터 데이터와 가챠 설정은 GitHub 레포를 jsDelivr CDN으로 서빙합니다. 앱이 서버 없이 직접 fetch합니다.

```
베이스 URL: https://cdn.jsdelivr.net/gh/LoxaLovecarstone/Ehrpis-helper-backend@main/

data/characters/index.json         ← 전체 캐릭터 목록 (66명)
data/characters/icons/0001.png     ← 캐릭터 아이콘
data/gacha/banner_config.json      ← 확률·천장 설정
data/gacha/starlight_config.json   ← 별빛 수치 설정
data/gacha/gacha_packages.json     ← 인앱 패키지 목록
```

main 브랜치에 머지하면 CDN에 자동 반영됩니다 (캐시 최대 24시간).

---

## 로컬 실행

```bash
pip install -r requirements.txt

# serviceAccountKey.json 을 프로젝트 루트에 배치 (Firebase 콘솔에서 발급)
python main.py
```

dev Firebase만 사용하려면 `DEV_ONLY=true` 환경변수를 설정합니다 (prod FCM 미발송).

```powershell
# Windows PowerShell
$env:DEV_ONLY="true"; python main.py
```

GitHub Actions 환경에서는 `FIREBASE_KEY` / `FIREBASE_KEY_DEV` Secret에 서비스 계정 JSON을 등록합니다.
