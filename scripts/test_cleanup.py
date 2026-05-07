import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
os.chdir(ROOT)

import firebase_admin
from firebase_admin import credentials, firestore

KEY_FILES = [
    # !!! main 머지 전 반드시 주석 해제 !!!
    ("serviceAccountKey.json", "prod"),
    ("serviceAccountKey_dev.json", "dev"),
]

for key_file, name in KEY_FILES:
    if not os.path.exists(key_file):
        print(f"[{name}] 키 파일 없음 → 스킵")
        continue
    cred = credentials.Certificate(key_file)
    app = firebase_admin.initialize_app(cred, name=name)
    db = firestore.client(app=app)
    doc_ref = db.collection("coupons").document("99999")
    if doc_ref.get().exists:
        doc_ref.delete()
        print(f"[{name}] feed_id 99999 삭제 완료")
    else:
        print(f"[{name}] feed_id 99999 없음")
