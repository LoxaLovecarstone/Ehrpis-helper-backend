import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.join(os.path.dirname(__file__), "..", "data")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_map(data, key="id"):
    return {item[key]: item for item in data}


characters = load(os.path.join(BASE, "characters", "index.json"))
classes    = make_map(load(os.path.join(BASE, "common", "classes.json")))
elements   = make_map(load(os.path.join(BASE, "common", "elements.json")))
roles      = make_map(load(os.path.join(BASE, "common", "roles.json")))

RARITY_STARS = {0: "?", 1: "★", 2: "★★", 3: "★★★", 4: "★★★★", 5: "★★★★★"}
RARITY_LABEL = {5: "5성", 4: "4성", 3: "3성", 2: "2성", 1: "1성", 0: "미정"}

# ── 정렬 기준: 레어리티 내림차순 → id 오름차순
characters.sort(key=lambda c: (-c["rarity"], c["id"]))

def fmt_char(c):
    rarity  = c["rarity"]
    stars   = RARITY_STARS.get(rarity, "?")
    cls     = classes.get(c["class_id"], {}).get("name_ko", "?")
    elem    = elements.get(c["element_id"], {}).get("name_ko", "없음")
    role_list = [roles.get(r, {}).get("name_ko", "?") for r in c["role_ids"]] or ["-"]
    flags   = []
    if c.get("is_limited"):
        flags.append("한정")
    if not c.get("is_gacha"):
        flags.append("비가챠")
    flag_str = f"  [{', '.join(flags)}]" if flags else ""

    return (
        f"  #{c['id']:>3}  {stars:<5}  {c['name_ko']:<10}"
        f"  클래스:{cls:<3}  속성:{elem:<2}  역할:{'/'.join(role_list)}{flag_str}"
    )


current_rarity = None
for c in characters:
    if c["rarity"] != current_rarity:
        current_rarity = c["rarity"]
        label  = RARITY_LABEL.get(current_rarity, f"{current_rarity}성")
        stars  = RARITY_STARS.get(current_rarity, "?")
        print(f"\n{'─'*60}")
        print(f"  {label}  ({stars})")
        print(f"{'─'*60}")
    print(fmt_char(c))

print()