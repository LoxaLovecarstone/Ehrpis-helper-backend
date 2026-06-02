from datetime import datetime, timezone, timedelta

import firebase_admin
from firebase_admin import credentials, firestore, messaging

KST = timezone(timedelta(hours=9))

_apps: dict = {}

APP_DATA = "app_data"
ACTIVE_COUPONS = "active_coupons"


def init_app(key_file: str, name: str) -> firebase_admin.App:
    if name in _apps:
        return _apps[name]
    cred = credentials.Certificate(key_file)
    app = firebase_admin.initialize_app(cred, name=name)
    _apps[name] = app
    return app


def get_db(app: firebase_admin.App):
    return firestore.client(app=app)


def is_coupon_expired(expiry_end: str | None) -> bool:
    if not expiry_end:
        return False
    try:
        dt = datetime.strptime(expiry_end, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
        return dt < datetime.now(KST)
    except ValueError:
        return False


def get_saved_feed_ids(db) -> set:
    """active_coupons를 1회 읽어 feed_id set 반환. 루프 전 한 번만 호출."""
    doc = db.collection(APP_DATA).document(ACTIVE_COUPONS).get()
    if not doc.exists:
        return set()
    items = doc.get("items") or []
    return {item["feed_id"] for item in items}


def is_already_saved(feed_id: int, cached_ids: set) -> bool:
    return feed_id in cached_ids


def save_coupon(post: dict, db):
    item = {
        "feed_id": post["feed_id"],
        "title": post["title"],
        "coupons": post["coupons"],
        "expiry_start": post["expiry"]["start"],
        "expiry_end": post["expiry"]["end"],
        "link": post["link"],
        "reward_types": post.get("reward_types", []),
        "created_date": post["created_date"],
    }
    db.collection(APP_DATA).document(ACTIVE_COUPONS).set(
        {
            "items": firestore.ArrayUnion([item]),
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    print(f"저장 완료: {post['title']}")


def send_fcm_notification(post: dict, app: firebase_admin.App):
    message = messaging.Message(
        data={
            "title": "🎫 새 쿠폰 도착!",
            "body": f"{', '.join(post['coupons'])}  |  {post['expiry']['end']}까지",
            "route": "coupon_list",
            "feed_id": str(post["feed_id"]),
            "coupons": ",".join(post["coupons"]),
            "expiry_end": post["expiry"]["end"] or "",
            "link": post["link"],
        },
        topic="coupons",
        android=messaging.AndroidConfig(
            priority="high",
        ),
    )
    messaging.send(message, app=app)
    print(f"FCM 발송 완료: {post['title']}")


"""
파이썬 콘솔에서 다음을 실행해서 테스트
from importlib import reload
import crawler.firebase_client as fc
reload(fc)
fc.test_fcm_notification()
"""
def test_fcm_notification():
    app = init_app("serviceAccountKey.json", "prod")
    post = {
        "feed_id": 99999,
        "title": "[리딤] 테스트 쿠폰",
        "coupons": ["TESTCODE123"],
        "expiry": {"start": "2026-04-13", "end": "2026-12-31 23:59"},
        "link": "https://game.naver.com/lounge/Ehrpis/board/25",
    }
    send_fcm_notification(post, app)
