import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
os.chdir(ROOT)

from crawler.firebase_client import init_app, get_db, save_coupon, send_fcm_notification

DUMMY_POST = {
    "feed_id": 99999,
    "title": "[테스트] 더미 쿠폰",
    "coupons": ["TESTCODE123"],
    "expiry": {"start": "2026-04-30", "end": "2026-12-31 23:59"},
    "link": "https://game.naver.com/lounge/Ehrpis/board/25",
    "reward_types": [],
    "created_date": "2026-04-30",
}

KEY_FILES = [
    ("serviceAccountKey.json", "prod"),
    ("serviceAccountKey_dev.json", "dev"),
]

for key_file, name in KEY_FILES:
    if not os.path.exists(key_file):
        print(f"[{name}] 키 파일 없음 → 스킵")
        continue
    app = init_app(key_file, name)
    db = get_db(app)
    save_coupon(DUMMY_POST, db)
    send_fcm_notification(DUMMY_POST, app)
    print(f"[{name}] 완료")
