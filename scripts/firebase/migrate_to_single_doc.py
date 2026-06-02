"""
coupons 컬렉션 → app_data/active_coupons 일회성 마이그레이션.

dev만:  DEV_ONLY=true python scripts/firebase/migrate_to_single_doc.py
전체:   python scripts/firebase/migrate_to_single_doc.py
"""
import os
import firebase_admin
from firebase_admin import credentials, firestore

DEV_ONLY = os.getenv("DEV_ONLY") == "true"
KEY_FILES = [("serviceAccountKey_dev.json", "dev")] if DEV_ONLY else [
    ("serviceAccountKey.json", "prod"),
    ("serviceAccountKey_dev.json", "dev"),
]

APP_DATA = "app_data"
ACTIVE_COUPONS = "active_coupons"


def migrate(db, name: str):
    docs = list(db.collection("coupons").stream())
    if not docs:
        print(f"[{name}] coupons 컬렉션 비어 있음 → 스킵")
        return

    ref = db.collection(APP_DATA).document(ACTIVE_COUPONS)
    existing_doc = ref.get()
    existing_items = existing_doc.get("items") if existing_doc.exists else []
    existing_ids = {item["feed_id"] for item in (existing_items or [])}

    new_items = []
    for doc in docs:
        data = doc.to_dict()
        feed_id = data.get("feed_id")
        if feed_id in existing_ids:
            continue
        new_items.append({
            "feed_id": feed_id,
            "title": data.get("title", ""),
            "coupons": data.get("coupons", []),
            "expiry_start": data.get("expiry_start"),
            "expiry_end": data.get("expiry_end"),
            "link": data.get("link", ""),
            "reward_types": data.get("reward_types", []),
            "created_date": data.get("created_date", ""),
        })

    if not new_items:
        print(f"[{name}] 이미 마이그레이션 완료 (기존 {len(existing_ids)}개)")
        return

    if existing_doc.exists:
        ref.update({
            "items": firestore.ArrayUnion(new_items),
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        print(f"[{name}] 마이그레이션 완료: 기존 {len(existing_ids)}개 + 신규 {len(new_items)}개")
    else:
        ref.set({
            "items": new_items,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        print(f"[{name}] 마이그레이션 완료: {len(new_items)}개")


def main():
    for key_file, name in KEY_FILES:
        if not os.path.exists(key_file):
            print(f"[{name}] 키 파일 없음 → 스킵")
            continue
        cred = credentials.Certificate(key_file)
        app = firebase_admin.initialize_app(cred, name=name)
        db = firestore.client(app=app)
        migrate(db, name)


if __name__ == "__main__":
    main()
