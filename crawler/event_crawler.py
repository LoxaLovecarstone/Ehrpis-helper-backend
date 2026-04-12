import httpx
from html import unescape
import emoji

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Referer": "https://game.naver.com/lounge/Ehrpis/board/4",
    "Origin": "https://game.naver.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "front-client-platform-type": "PC",
    "front-client-product-type": "web",
    "if-modified-since": "Mon, 26 Jul 1997 05:00:00 GMT",
    "deviceid": "0b461c88-4989-43d7-bbca-29f7f1a135e0",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}


def clean_title(title: str) -> str:
    title = unescape(title)
    title = emoji.replace_emoji(title, replace="")
    return title.strip()


async def fetch_event_posts(limit: int = 25) -> list[dict]:
    """자유게시판(boardId=4) 최신 게시물 가져오기 (쿠키 불필요 테스트)"""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        url = (
            f"https://comm-api.game.naver.com/nng_main/v1/community/lounge/Ehrpis/feed"
            f"?boardId=4&buffFilteringYN=N&limit={limit}&offset=0&order=NEW"
        )
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()["content"]

        posts = []
        for item in data["feeds"]:
            feed = item["feed"]
            posts.append({
                "feed_id": feed["feedId"],
                "title": clean_title(feed.get("title", "")),
                "link": item["feedLink"]["pc"],
                "created_date": feed.get("createdDate"),
            })

        return posts