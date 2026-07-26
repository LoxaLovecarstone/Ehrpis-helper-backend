from html import unescape
import emoji
import httpx
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://game.naver.com/lounge/Ehrpis/board/25",
}

LIST_API = "https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed?boardId=25&buffFilteringYN=N&limit={limit}&offset={offset}&order=NEW"
DETAIL_API = "https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed/{feed_id}"


def clean_title(title: str) -> str:
    """HTML 엔티티 디코딩 후 이모지 제거 및 공백 정리"""
    title = unescape(title)
    title = emoji.replace_emoji(title, replace="")
    return title.strip()


def extract_coupons_from_html(html: str) -> list[str]:
    """본문 HTML에서 쿠폰 코드 추출"""
    soup = BeautifulSoup(html, "html.parser")
    # separator=' ': 태그 경계마다 공백 삽입 → 한글이 \w라 \b가 깨지는 문제 방지
    text = soup.get_text(separator=' ')

    # "코드명: [GIFTS0406]" 또는 "쿠폰 코드 : MYHEART" 패턴
    pattern1 = re.findall(r'(?:코드명|쿠폰\s*코드)[^\w]*\[?([A-Z0-9]{4,20})\]?', text)

    # 대문자+숫자 조합 6~20자리 (일반 패턴)
    pattern2 = re.findall(r'\b[A-Z][A-Z0-9]{5,19}\b', text)

    # 두 패턴 합치고 중복 제거, pattern1 우선
    all_codes = list(dict.fromkeys(pattern1 + pattern2))
    return all_codes


GACHA_ITEMS = ["오팔", "운명의 그림자", "기적의 그림자"]


def extract_reward_types(html: str) -> list[str]:
    types = [item for item in GACHA_ITEMS if item in html]
    return types if types else ["기타"]


def extract_expiry(html: str) -> dict:
    """보상 수령 기간 / 쿠폰 사용 기간 추출 → 시작일/종료일 분리"""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    match = re.search(
        r'(?:보상 수령 기간|쿠폰 사용 기간)\s*[:\s]*'
        r'([\d\-.]+(?:\([가-힣]+\))?)\s*~\s*(\d{4}[.\-]\d{2}[.\-]\d{2}(?:\([가-힣]+\))?(?:\s+\d{2}:\d{2}(?::\d{2})?)?)(?:\s*까지)?',
        text,
    )
    if not match:
        return {"start": None, "end": None}

    # 요일 표기 "(금)" 등 제거
    start_str = re.sub(r'\([가-힣]+\)', '', match.group(1)).strip()
    end_str = re.sub(r'\([가-힣]+\)', '', match.group(2)).strip()

    # 날짜 파싱 (대시: 2026-04-08, 점: 2026.04.08 두 형태 모두 처리)
    start = None
    for fmt in ["%Y-%m-%d", "%Y.%m.%d"]:
        try:
            start = datetime.strptime(start_str, fmt)
            break
        except ValueError:
            continue

    # 종료일: 초 단위 포함 형태도 처리
    end = None
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M", "%Y-%m-%d", "%Y.%m.%d"]:
        try:
            end = datetime.strptime(end_str, fmt)
            break
        except ValueError:
            continue

    return {
        "start": start.strftime("%Y-%m-%d") if start else None,
        "end": end.strftime("%Y-%m-%d %H:%M") if end else None,
    }


async def fetch_coupon_posts(known_feed_ids: set = frozenset()) -> list[dict]:
    """지원 코드 게시판(boardId=25)을 최신순으로 순회하며 쿠폰 게시글을 수집한다.

    게시판 자체가 지원 코드 전용이라 제목 헤더(예: "[리딤]")로는 필터링하지 않고,
    본문에서 실제 쿠폰 코드가 추출되는 게시글만 채택한다. "[리딤]" 같은 고정 헤더가
    없는 제목(예: "고스트킹 합류 기념 특별 쿠폰")도 이 방식이면 놓치지 않는다.

    게시글은 최신순 정렬이므로, 이미 저장된 feed_id(known_feed_ids)를 만나면
    그 이후는 전부 과거 게시글이라 즉시 순회를 멈춘다 (매 폴링마다 게시판 전체
    이력을 상세 조회하지 않기 위함).
    """
    async with httpx.AsyncClient(headers=HEADERS) as client:
        coupon_posts = []
        page_offset = 0
        limit = 25

        while True:
            url = LIST_API.format(limit=limit, offset=page_offset)
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()["content"]

            feeds = data["feeds"]

            for item in feeds:
                feed = item["feed"]
                feed_id = feed["feedId"]

                if feed_id in known_feed_ids:
                    return coupon_posts

                title = clean_title(feed.get("title", ""))

                detail_resp = await client.get(
                    DETAIL_API.format(feed_id=feed_id)
                )
                detail_resp.raise_for_status()
                detail = detail_resp.json()["content"]["feed"]

                contents_html = detail.get("contents", "")
                coupons = extract_coupons_from_html(contents_html)
                if not coupons:
                    continue

                expiry = extract_expiry(contents_html)
                reward_types = extract_reward_types(contents_html)

                coupon_posts.append({
                    "feed_id": feed_id,
                    "title": title,
                    "coupons": coupons,
                    "expiry": expiry,
                    "reward_types": reward_types,
                    "created_date": feed.get("createdDate"),
                    "link": item["feedLink"]["pc"],
                })

            page_offset += 1
            if len(feeds) < limit:
                break

        return coupon_posts