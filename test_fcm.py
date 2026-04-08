import firebase_admin
from firebase_admin import credentials, messaging

# 1. Firebase 초기화 (이미 초기화되었는지 확인 후 실행)
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

def send_test_notification():
    # 2. 테스트용 더미 데이터
    dummy_post = {
        "feed_id": 999999,
        "title": "🧪 테스트: 에르피스 신규 쿠폰",
        "coupons": ["TEST-CODE-2026", "WELCOME-HERO"],
        "expiry": {
            "end": "2026-12-31 23:59"
        },
        "link": "https://game.naver.com/lounge/Ehrpis/board/25"
    }

    # 3. 메시지 구성
    message = messaging.Message(
        notification=messaging.Notification(
            title="🎫 새 쿠폰 도착! (테스트)",
            body=f"{', '.join(dummy_post['coupons'])} | {dummy_post['expiry']['end']}까지",
        ),
        data={
            "route": "coupon_list",
            "feed_id": str(dummy_post["feed_id"]),
            "link": dummy_post["link"],
        },
        topic="coupons",
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                click_action="OPEN_COUPON_LIST",
                channel_id="coupon_channel",  # 앱의 CHANNEL_ID와 일치
                default_sound=True,
                default_vibrate_timings=True,
            ),
        ),
    )

    # 4. 발송
    try:
        response = messaging.send(message)
        print(f"✅ 테스트 알림 발송 성공! 서버 응답: {response}")
    except Exception as e:
        print(f"❌ 발송 실패: {e}")

if __name__ == "__main__":
    send_test_notification()