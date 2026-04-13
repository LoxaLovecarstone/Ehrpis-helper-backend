import firebase_admin
from firebase_admin import credentials, firestore, messaging
_initialized = False

def get_db():
    global _initialized
    if not _initialized:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        _initialized = True
    return firestore.client()


def is_already_saved(feed_id: int) -> bool:
    """이미 저장된 쿠폰인지 확인 (중복 방지)"""
    db = get_db()
    doc = db.collection("coupons").document(str(feed_id)).get()
    return doc.exists


def save_coupon(post: dict):
    db = get_db()
    db.collection("coupons").document(str(post["feed_id"])).set({
        "feed_id": post["feed_id"],
        "title": post["title"],
        "coupons": post["coupons"],
        "expiry_start": post["expiry"]["start"],  # "2026-02-05"
        "expiry_end": post["expiry"]["end"],       # "2026-08-05 23:59"
        "link": post["link"],
        "created_date": post["created_date"],
        "notified": False,
    })
    print(f"저장 완료: {post['title']}")




def is_event_seen(feed_id: int) -> bool:
    """이미 처리한 이벤트 게시물인지 확인"""
    db = get_db()
    doc = db.collection("event_seen").document(str(feed_id)).get()
    return doc.exists


def mark_event_seen(feed_id: int, title: str):
    """이벤트 게시물을 처리 완료로 기록"""
    db = get_db()
    db.collection("event_seen").document(str(feed_id)).set({
        "feed_id": feed_id,
        "title": title,
    })


def send_event_fcm_notification(post: dict):
    message = messaging.Message(
        notification=messaging.Notification(
            title="[테스트] 새 이벤트 게시물",
            body=post["title"],
        ),
        data={
            "feed_id": str(post["feed_id"]),
            "link": post["link"],
        },
        topic="test",
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="coupon_channel",
                default_sound=True,
                default_vibrate_timings=True,
            ),
        ),
    )
    messaging.send(message)
    print(f"FCM 발송 완료 (test topic): {post['title']}")


def send_fcm_notification(post: dict):
    message = messaging.Message(
        notification=messaging.Notification(
            title="🎫 새 쿠폰 도착!",
            body=f"{', '.join(post['coupons'])}  |  {post['expiry']['end']}까지",
        ),
        data={
            "route": "coupon_list",
            "feed_id": str(post["feed_id"]),
            "coupons": ",".join(post["coupons"]),
            "expiry_end": post["expiry"]["end"] or "",
            "link": post["link"],
        },
        topic="coupons",
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                click_action="OPEN_COUPON_LIST",
                channel_id="coupon_channel",
                default_sound=True,
                default_vibrate_timings=True,
            ),
        ),
    )
    messaging.send(message)
    print(f"FCM 발송 완료: {post['title']}")