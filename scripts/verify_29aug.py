import json
from collections import Counter

def nonlatin(s): return any(ord(c) > 0x7F for c in s)

all_reels = []
for name in ['29Aug1.json','29Aug2.json']:
    d = json.load(open(rf'C:\ProjectComfy\{name}', encoding='utf-8'))
    reels = d['reels']
    all_reels += reels
    print(f'{name}: {len(reels)} reels')

ids = [r['id'] for r in all_reels]
print(f'TOTAL={len(all_reels)} unique_ids={len(set(ids))} EXPECT 24 reels')
print('CHANNELS:', dict(Counter(r['channel'] for r in all_reels)))
dups = sorted({i for i in ids if ids.count(i)>1})
print('DUPLICATE ids across files:', dups[:24])

print('\n=== schema fields (first reel) ===')
r = all_reels[0]
print('top keys:', sorted(r.keys()))
print('words[0]:', r['words'][0])
print('lines type:', type(r['lines']).__name__, 'len', len(r['lines']), 'sample:', r['lines'][0][:60])
print('scenes[0] keys:', sorted(r['scenes'][0].keys()))

print('\n=== per-reel completeness ===')
bad = []
for r in all_reels:
    for f in ['id','channel','pair','topic','seed','voice_src','voice_tgt','voice_src2','voice_tgt2','music','words','lines','scenes']:
        if f not in r: bad.append(f'{r["id"]}: missing {f}')
    if len(r.get('words',[])) != 3: bad.append(f'{r["id"]}: words={len(r.get("words",[]))}')
    if len(r.get('lines',[])) != 3: bad.append(f'{r["id"]}: lines={len(r.get("lines",[]))}')
    if len(r.get('scenes',[])) != 4: bad.append(f'{r["id"]}: scenes={len(r.get("scenes",[]))}')
    for w in r.get('words',[]):
        for f in ['term','translation']:
            if f not in w: bad.append(f'{r["id"]}: word missing {f}')
    for sc in r.get('scenes',[]):
        if 'prompt' not in sc: bad.append(f'{r["id"]}: scene missing prompt')
print('ISSUES:', len(bad))
for b in bad[:25]: print('  -', b)

print('\n=== orientation check ===')
X2EN = ('arabic-to-english','chinese-to-english','spanish-to-english')
EN2X = ('english-to-arabic','english-to-chinese','english-to-spanish')
L = {'ar-SA':'ar','zh-CN':'zh','en-US':'en','es-ES':'es'}
o = 0
for r in all_reels:
    # word.term should be foreign (for X2EN) or English (for EN2X)
    for w in r['words']:
        t, tr = w.get('term',''), w.get('translation','')
        if r['channel'] in X2EN:
            if not nonlatin(t) and L.get(r['voice_src'][:5]) in ('ar','zh'): o += 1; print('  X2EN term not foreign:', r['id'], repr(t[:20]))
        if r['channel'] in EN2X:
            if nonlatin(t): o += 1; print('  EN2X term not English:', r['id'], repr(t[:20]))
print('orientation issues:', o)

print('\n=== topics ===')
for r in all_reels:
    print(f"  {r['id']} {r['channel']} = {r['topic']}")
