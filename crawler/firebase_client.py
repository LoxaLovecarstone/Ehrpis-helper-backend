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
        "reward_types": post.get("reward_types", []),
        "created_date": post["created_date"],
        "notified": False,
    })
    print(f"저장 완료: {post['title']}")




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


"""
파이썬 콘솔에서 다음을 실행해서 테스트
from importlib import reload                                                                                                                                    
import crawler.firebase_client as fc
reload(fc)                                                                                                                                                      
fc.test_fcm_notification()  
"""
def test_fcm_notification():
    get_db()  # Firebase 초기화
    post = {
        "feed_id": 99999,
        "title": "[리딤] 테스트 쿠폰",
        "coupons": ["TESTCODE123"],
        "expiry": {"start": "2026-04-13", "end": "2026-12-31 23:59"},
        "link": "https://game.naver.com/lounge/Ehrpis/board/25",
    }
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