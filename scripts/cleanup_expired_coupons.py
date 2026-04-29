import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
BATCH_SIZE = 500

KEY_FILES = [
    ("serviceAccountKey.json", "prod"),
    ("serviceAccountKey_dev.json", "dev"),
]


def cleanup(db) -> int:
    now = datetime.now(KST)
    to_delete = []

    for doc in db.collection("coupons").stream():
        expiry_end = doc.get("expiry_end")
        if not expiry_end:
            continue
        try:
            expiry_dt = datetime.strptime(expiry_end, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
            if expiry_dt < now:
                to_delete.append(doc.reference)
        except ValueError:
            continue

    for i in range(0, len(to_delete), BATCH_SIZE):
        batch = db.batch()
        for ref in to_delete[i : i + BATCH_SIZE]:
            batch.delete(ref)
        batch.commit()

    return len(to_delete)


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
