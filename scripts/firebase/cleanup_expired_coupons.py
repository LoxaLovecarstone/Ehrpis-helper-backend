import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

DEV_ONLY = os.getenv("DEV_ONLY") == "true"
KEY_FILES = [("serviceAccountKey_dev.json", "dev")] if DEV_ONLY else [
    ("serviceAccountKey.json", "prod"),
    ("serviceAccountKey_dev.json", "dev"),
]

APP_DATA = "app_data"
ACTIVE_COUPONS = "active_coupons"


def _is_expired(item: dict, now: datetime) -> bool:
    expiry_end = item.get("expiry_end")
    if not expiry_end:
        return False
    try:
        expiry_dt = datetime.strptime(expiry_end, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
        return expiry_dt < now
    except ValueError:
        return False


def cleanup(db) -> int:
    now = datetime.now(KST)
    ref = db.collection(APP_DATA).document(ACTIVE_COUPONS)

    # Transaction으로 read-modify-write 원자 처리
    # cleanup(00:00 KST)과 크롤러(08:30 / 15:30 KST)는 스케줄상 겹치지 않지만,
    # 혹시라도 동시 실행될 경우 ArrayUnion으로 추가된 항목이 덮어써지는 것을 방지
    @firestore.transactional
    def _run(transaction, ref):
        doc = ref.get(transaction=transaction)
        if not doc.exists:
            return 0
        items = doc.get("items") or []
        active = [item for item in items if not _is_expired(item, now)]
        expired_count = len(items) - len(active)
        if expired_count > 0:
            transaction.update(ref, {
                "items": active,
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
        return expired_count

    transaction = db.transaction()
    return _run(transaction, ref)


def main():
    for key_file, name in KEY_FILES:
        if not os.path.exists(key_file):
            continue
        cred = credentials.Certificate(key_file)
        app = firebase_admin.initialize_app(cred, name=name)
        db = firestore.client(app=app)
        deleted = cleanup(db)
        if deleted:
            print(f"[{name}] 삭제 완료: {deleted}개")
        else:
            print(f"[{name}] 삭제할 만료 쿠폰 없음")


if __name__ == "__main__":
    main()
