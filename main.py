import asyncio
import datetime
import os
from crawler.coupon_crawler import fetch_coupon_posts
from crawler.firebase_client import init_app, get_db, get_saved_feed_ids, is_already_saved, is_coupon_expired, save_coupon, save_coupon_legacy, send_fcm_notification

DEV_ONLY = os.getenv("DEV_ONLY") == "true"
KEY_FILES = [("serviceAccountKey_dev.json", "dev")] if DEV_ONLY else [
    ("serviceAccountKey.json", "prod"),
    ("serviceAccountKey_dev.json", "dev"),
]

KST = datetime.timezone(datetime.timedelta(hours=9))
POLL_INTERVAL = 300


async def crawl_once(dbs, apps, prod_db):
    print(f"[{datetime.datetime.now(KST).strftime('%H:%M:%S')}] 크롤링 시작")
    cached_ids = get_saved_feed_ids(prod_db)
    posts = await fetch_coupon_posts(cached_ids)

    if not posts:
        print("쿠폰 게시글 없음")
        return

    new_count = 0
    for post in posts:
        if is_coupon_expired(post["expiry"]["end"]):
            print(f"만료된 쿠폰 스킵: {post['title']}")
            continue

        if is_already_saved(post["feed_id"], cached_ids):
            print("이미 저장됨 → 이후는 스킵")
            break

        for db, app in zip(dbs, apps):
            save_coupon(post, db)
            save_coupon_legacy(post, db)
            send_fcm_notification(post, app)
        cached_ids.add(post["feed_id"])
        new_count += 1

    print(f"신규 {new_count}개 저장")


async def main():
    apps = [
        init_app(key_file, name)
        for key_file, name in KEY_FILES
        if os.path.exists(key_file)
    ]
    dbs = [get_db(app) for app in apps]
    prod_db = dbs[0]

    now = datetime.datetime.now(KST)
    if now.hour < 12:
        deadline = now.replace(hour=11, minute=20, second=0, microsecond=0)
    else:
        deadline = now.replace(hour=18, minute=0, second=0, microsecond=0)

    while True:
        try:
            await crawl_once(dbs, apps, prod_db)
        except Exception as e:
            print(f"크롤링 에러 ({POLL_INTERVAL}초 후 재시도): {e}")
        if datetime.datetime.now(KST) >= deadline:
            break
        await asyncio.sleep(POLL_INTERVAL)

    print(f"{deadline.strftime('%H:%M')} KST 초과 → 종료")


if __name__ == "__main__":
    asyncio.run(main())
