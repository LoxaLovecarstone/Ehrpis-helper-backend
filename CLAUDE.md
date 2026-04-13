# TODO

- 자유게시판(boardId=4) 크롤링 코드는 FCM 테스트용임. 크롤링 성공 테스트 완료 후 삭제할 것.
  - `crawler/event_crawler.py`
  - `crawler/firebase_client.py` — `is_event_seen`, `mark_event_seen`, `send_event_fcm_notification`
  - `main_event.py`
  - `.github/workflows/crawl_event.yml`
