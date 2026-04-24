import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
BATCH_SIZE = 500


def main():
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()

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

    if to_delete:
        print(f"삭제 완료: {len(to_delete)}개")
    else:
        print("삭제할 만료 쿠폰 없음")


if __name__ == "__main__":
    main()
