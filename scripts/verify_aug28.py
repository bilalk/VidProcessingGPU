import json

SRC = r'C:\ProjectComfy\reels'
X2EN = {'arabic-to-english','chinese-to-english','spanish-to-english'}
EN2X = {'english-to-arabic','english-to-chinese','english-to-spanish'}

def nonlatin(s):
    return any(ord(c) > 0x7F for c in s)

all_reels = []
for name in ['manifest_aug28_g1.json','manifest_aug28_g2.json']:
    d = json.load(open(rf'{SRC}\{name}', encoding='utf-8'))
    all_reels += d['reels']
    print(f'{name}: {len(d["reels"])} reels')

ids = [r['id'] for r in all_reels]
print(f'TOTAL reels = {len(all_reels)}, unique ids = {len(set(ids))}')
dups = [i for i in set(ids) if ids.count(i) > 1]
print('DUPLICATE IDs:', dups if dups else 'NONE')

# channel distribution
from collections import Counter
cc = Counter(r['channel'] for r in all_reels)
print('CHANNELS:', dict(cc))

print('\n=== per-reel check (orientation + fields) ===')
bad = []
for r in all_reels:
    # required fields
    for f in ['id','channel','pair','topic','seed','voice_src','voice_tgt','music','words','lines','scenes']:
        if f not in r:
            bad.append(f'{r["id"]}: MISSING {f}')
    if len(r.get('words',[])) != 3: bad.append(f'{r["id"]}: words!={r.get("words") and len(r["words"])}')
    if len(r.get('lines',[])) != 3: bad.append(f'{r["id"]}: lines!=3')
    if len(r.get('scenes',[])) != 4: bad.append(f'{r["id"]}: scenes!={len(r.get("scenes",[]))}')
    # orientation
    ch = r['channel']
    for i, ln in enumerate(r.get('lines',[])):
        if ch in EN2X:
            if nonlatin(ln['src']): bad.append(f'{r["id"]}: L{i+1}.src has non-latin (should be English)')
            if not nonlatin(ln['tgt']) and ch != 'english-to-spanish' and r['pair'].split("-")[1] in ('ar','zh'):
                bad.append(f'{r["id"]}: L{i+1}.tgt has NO non-latin (should be foreign)')
        elif ch in X2EN:
            if not nonlatin(ln['src']) and r['pair'].split("-")[0] in ('ar','zh'):
                bad.append(f'{r["id"]}: L{i+1}.src has NO non-latin (should be foreign)')
            if nonlatin(ln['tgt']): bad.append(f'{r["id"]}: L{i+1}.tgt has non-latin (should be English)')
print(f'ISSUES: {len(bad)}')
for b in bad[:40]:
    print('  -', b)

print('\n=== topics (24) ===')
seen = {}
for r in all_reels:
    ch = r['channel']
    seen.setdefault(ch, []).append((r['id'], r['topic']))
for ch, items in sorted(seen.items()):
    print(f'{ch}: ' + ', '.join(f'{i.split("-")[-1]}={t}' for i,t in sorted(items)))
