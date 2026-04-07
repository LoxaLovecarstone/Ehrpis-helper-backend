import asyncio
from crawler.coupon_crawler import fetch_coupon_posts
from crawler.firebase_client import is_already_saved, save_coupon, send_fcm_notification


async def main():
    print("크롤링 시작...")
    posts = await fetch_coupon_posts()

    if not posts:
        print("쿠폰 게시글 없음")
        return

    new_count = 0
    for post in posts:
        if is_already_saved(post["feed_id"]):
            print(f"이미 저장됨 → 이후는 스킵")
            break

        save_coupon(post)
        send_fcm_notification(post)
        new_count += 1

    print(f"\n완료: 신규 {new_count}개 저장")


if __name__ == "__main__":
    asyncio.run(main())