import asyncio
import os
from crawler.coupon_crawler import fetch_coupon_posts
from crawler.firebase_client import init_app, get_db, is_already_saved, save_coupon, send_fcm_notification

KEY_FILES = [
    ("serviceAccountKey.json", "prod"),
    ("serviceAccountKey_dev.json", "dev"),
]


async def main():
    print("크롤링 시작...")
    posts = await fetch_coupon_posts()

    if not posts:
        print("쿠폰 게시글 없음")
        return

    apps = [
        init_app(key_file, name)
        for key_file, name in KEY_FILES
        if os.path.exists(key_file)
    ]
    dbs = [get_db(app) for app in apps]
    prod_db = dbs[0]

    new_count = 0
    for post in posts:
        if is_already_saved(post["feed_id"], prod_db):
            print("이미 저장됨 → 이후는 스킵")
            break

        for db, app in zip(dbs, apps):
            save_coupon(post, db)
            send_fcm_notification(post, app)
        new_count += 1

    print(f"\n완료: 신규 {new_count}개 저장")


if __name__ == "__main__":
    asyncio.run(main())
