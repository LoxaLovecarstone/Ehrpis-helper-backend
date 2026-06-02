import json
import os

base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open(os.path.join(base, 'data/characters/index.json'), encoding='utf-8') as f:
    characters = json.load(f)

with open(os.path.join(base, 'data/common/character_tags.json'), encoding='utf-8') as f:
    tag_map = {t['id']: t for t in json.load(f)}

RARITY  = {5: '★5', 4: '★4', 3: '★3', 2: '★2', 1: '★1'}
CLASS   = {1: '수호', 2: '돌격', 3: '언령', 4: '사수'}
ROLE    = {1: '딜러', 2: '탱커', 3: '힐러', 4: '서포터'}
ELEMENT = {1: '수', 2: '화', 3: '목', 4: '광', 5: '암'}

unknown_ids = set()

for c in characters:
    roles = '/'.join(ROLE.get(r, str(r)) for r in c['role_ids'])
    tag_parts = []
    for tid in c.get('tag_ids', []):
        if tid in tag_map:
            t = tag_map[tid]
            tag_parts.append(f"{t['name_ko']}[{t['category']}]")
        else:
            tag_parts.append(f"❌UNKNOWN_ID:{tid}")
            unknown_ids.add(tid)

    limited = ' 한정' if c['is_limited'] else ''
    gacha   = '' if c['is_gacha'] else ' 비가챠'
    tags_str = ' · '.join(tag_parts) if tag_parts else '-'

    print(f"[{c['id']:02d}] {c['name_ko']:<10} {RARITY.get(c['rarity'], '?')} "
          f"{CLASS.get(c['class_id'], '?')} {ELEMENT.get(c['element_id'], '?')} "
          f"[{roles}]{limited}{gacha}")
    print(f"      {tags_str}")

print()
print(f"총 {len(characters)}명")
if unknown_ids:
    print(f"[!] 존재하지 않는 tag_id: {sorted(unknown_ids)}")
else:
    print("[OK] 모든 tag_id 유효")
