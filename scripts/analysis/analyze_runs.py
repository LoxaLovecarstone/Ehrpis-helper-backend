import csv
import json
import os
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CRON_SLOTS = [
    ((1, 7),  "10:07 KST"),
    ((1, 37), "10:37 KST"),
    ((2, 7),  "11:07 KST"),
    ((2, 37), "11:37 KST"),
    ((8, 7),  "17:07 KST"),
]

with open(os.path.join(ROOT, "scripts", "analysis", "runs.json"), encoding="utf-8") as f:
    runs = json.load(f)

scheduled = sorted(
    [r for r in runs if r["event"] == "schedule"],
    key=lambda r: r["createdAt"]
)

# 날짜별로 그룹핑 (UTC 기준)
by_date = defaultdict(list)
for run in scheduled:
    dt = datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00"))
    by_date[dt.date()].append(dt)

for d in by_date:
    by_date[d].sort()

# 날짜별로 실행 순서와 cron 순서를 매칭
delays_by_slot = defaultdict(list)
rows = []  # CSV용

for d, times in by_date.items():
    if len(times) != len(CRON_SLOTS):
        continue  # 5개 미만인 날 제외 (workflow_dispatch 혼입 등)

    for i, actual in enumerate(times):
        (h, m), label = CRON_SLOTS[i]
        expected = datetime(d.year, d.month, d.day, h, m,
                            tzinfo=actual.tzinfo)
        delay = (actual - expected).total_seconds() / 60
        delays_by_slot[label].append(delay)
        rows.append({
            "date": d.isoformat(),
            "slot": label,
            "expected_utc": expected.strftime("%H:%M"),
            "actual_utc": actual.strftime("%H:%M:%S"),
            "delay_min": round(delay, 1),
        })

CSV_PATH = os.path.join(ROOT, "mydocs", "github_actions_delays.csv")
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["date", "slot", "expected_utc", "actual_utc", "delay_min"])
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda r: (r["date"], r["slot"])))
print(f"CSV 저장: {CSV_PATH}\n")

print(f"총 scheduled 실행: {len(scheduled)}회")
print(f"날짜별 5개 완전한 날: {len([d for d in by_date if len(by_date[d]) == 5])}일\n")
print(f"{'슬롯':<12} {'횟수':>5} {'평균':>8} {'최소':>8} {'최대':>8}")
print("-" * 46)

summary_rows = []
for _, label in CRON_SLOTS:
    delays = delays_by_slot[label]
    if not delays:
        print(f"{label:<12} {'0':>5}")
        continue
    avg = sum(delays) / len(delays)
    print(f"{label:<12} {len(delays):>5} {avg:>7.1f}분 {min(delays):>7.1f}분 {max(delays):>7.1f}분")
    summary_rows.append({
        "slot": label,
        "count": len(delays),
        "avg_min": round(avg, 1),
        "min_min": round(min(delays), 1),
        "max_min": round(max(delays), 1),
    })

SUMMARY_PATH = os.path.join(ROOT, "mydocs", "github_actions_delays_summary.csv")
with open(SUMMARY_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["slot", "count", "avg_min", "min_min", "max_min"])
    writer.writeheader()
    writer.writerows(summary_rows)
print(f"\n요약 CSV 저장: {SUMMARY_PATH}")
