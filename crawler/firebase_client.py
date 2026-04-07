import firebase_admin
from firebase_admin import credentials, firestore

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