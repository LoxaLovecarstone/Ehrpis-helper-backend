import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)
os.chdir(ROOT)

import firebase_admin
from firebase_admin import credentials, firestore

DEV_ONLY = os.getenv("DEV_ONLY") == "true"
KEY_FILES = [("serviceAccountKey_dev.json", "dev")] if DEV_ONLY else [
    ("serviceAccountKey.json", "prod"),
    ("serviceAccountKey_dev.json", "dev"),
]

APP_DATA = "app_data"
ACTIVE_COUPONS = "active_coupons"

for key_file, name in KEY_FILES:
    if not os.path.exists(key_file):
        print(f"[{name}] 키 파일 없음 → 스킵")
        continue
    cred = credentials.Certificate(key_file)
    app = firebase_admin.initialize_app(cred, name=name)
    db = firestore.client(app=app)
    ref = db.collection(APP_DATA).document(ACTIVE_COUPONS)
    doc = ref.get()
    if not doc.exists:
        print(f"[{name}] active_coupons 문서 없음")
        continue
    items = (doc.to_dict() or {}).get("items") or []
    filtered = [item for item in items if item.get("feed_id") != 99999]
    if len(filtered) == len(items):
        print(f"[{name}] feed_id 99999 없음")
    else:
        ref.update({
            "items": filtered,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        print(f"[{name}] feed_id 99999 삭제 완료")
