import asyncio
from crawler.event_crawler import fetch_event_posts
from crawler.firebase_client import is_event_seen, mark_event_seen, send_event_fcm_notification


async def main():
    print("이벤트 게시판 크롤링 시작...")
    posts = await fetch_event_posts(limit=25)

    if not posts:
        print("게시물 없음")
        return

    new_count = 0
    for post in posts:
        if is_event_seen(post["feed_id"]):
            continue

        mark_event_seen(post["feed_id"], post["title"])
        send_event_fcm_notification(post)
        print(f"새 게시물 감지: {post['title']}")
        new_count += 1

    print(f"\n완료: 신규 {new_count}개 처리")


if __name__ == "__main__":
    asyncio.run(main())
