import httpx
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://game.naver.com/lounge/Ehrpis/board/25",
}

LIST_API = "https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed?boardId=25&buffFilteringYN=N&limit=25&offset=0&order=NEW"
DETAIL_API = "https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed/{feed_id}"


def is_coupon_post(title: str) -> bool:
    return "[리딤]" in title


def extract_coupons_from_html(html: str) -> list[str]:
    """본문 HTML에서 쿠폰 코드 추출"""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    # "코드명: [GIFTS0406]" 패턴
    pattern1 = re.findall(r'코드명[^\w]*\[?([A-Z0-9]{4,20})\]?', text)

    # 대문자+숫자 조합 6~20자리 (일반 패턴)
    pattern2 = re.findall(r'\b[A-Z][A-Z0-9]{5,19}\b', text)

    # 두 패턴 합치고 중복 제거, pattern1 우선
    all_codes = list(dict.fromkeys(pattern1 + pattern2))
    return all_codes


def extract_expiry(html: str) -> dict:
    """보상 수령 기간 추출 → 시작일/종료일 분리"""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    match = re.search(r'보상 수령 기간\s*[:\s]*([\d\-]+)\s*~\s*([\d\-\s:]+)', text)
    if not match:
        return {"start": None, "end": None}

    start_str = match.group(1).strip()
    end_str = match.group(2).strip()

    # 날짜 파싱
    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
    except ValueError:
        start = None

    # 종료일은 "2026-04-08 23:59" 또는 "2026-08-05" 두 형태
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d"]:
        try:
            end = datetime.strptime(end_str, fmt)
            break
        except ValueError:
            end = None

    return {
        "start": start.strftime("%Y-%m-%d") if start else None,
        "end": end.strftime("%Y-%m-%d %H:%M") if end else None,
    }


async def fetch_coupon_posts() -> list[dict]:
    async with httpx.AsyncClient(headers=HEADERS) as client:
        coupon_posts = []
        offset = 0
        limit = 25

        while True:
            url = f"https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed?boardId=25&buffFilteringYN=N&limit={limit}&offset={offset}&order=NEW"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()["content"]

            feeds = data["feeds"]
            total = data["totalCount"]

            for item in feeds:
                feed = item["feed"]
                title = feed.get("title", "")

                if not is_coupon_post(title):
                    continue

                feed_id = feed["feedId"]

                detail_resp = await client.get(
                    DETAIL_API.format(feed_id=feed_id)
                )
                detail_resp.raise_for_status()
                detail = detail_resp.json()["content"]["feed"]

                contents_html = detail.get("contents", "")
                coupons = extract_coupons_from_html(contents_html)
                expiry = extract_expiry(contents_html)

                coupon_posts.append({
                    "feed_id": feed_id,
                    "title": title,
                    "coupons": coupons,
                    "expiry": expiry,
                    "created_date": feed.get("createdDate"),
                    "link": item["feedLink"]["pc"],
                })

            offset += limit
            if offset >= total:
                break

        return coupon_posts