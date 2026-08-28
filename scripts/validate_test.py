import json, sys
from collections import Counter

path = r'C:\ProjectComfy\test.json'
try:
    d = json.load(open(path, encoding='utf-8'))
except Exception as e:
    print('INVALID JSON:', e); sys.exit(1)

reels = d.get('reels', [])
print('VALID JSON: yes')
print(f'TOTAL reels: {len(reels)}')
print(f'CHANNELS: {dict(Counter(r["channel"] for r in reels))}')
ids = [r['id'] for r in reels]
print(f'UNIQUE ids: {len(set(ids))} / {len(ids)}  (dups: {[i for i in set(ids) if ids.count(i)>1] or "none"})')

print('\n=== schema of first reel (top-level keys) ===')
print(sorted(reels[0].keys()))

print('\n=== per-reel field completeness ===')
REQ = ['id','channel','pair','topic','seed','voice_src','voice_tgt','voice_src2','voice_tgt2','music','words','lines','scenes']
bad = []
for r in reels:
    for f in REQ:
        if f not in r: bad.append(f'{r["id"]}: missing {f}')
    if len(r.get('words',[])) != 4: bad.append(f'{r["id"]}: words.len={len(r.get("words",[]))} (expect 4)')
    if len(r.get('lines',[])) != 2: bad.append(f'{r["id"]}: lines.len={len(r.get("lines",[]))} (expect 2)')
    if len(r.get('scenes',[])) != 1: bad.append(f'{r["id"]}: scenes.len={len(r.get("scenes",[]))} (expect 1)')
    # lines structure
    for ln in r.get('lines',[]):
        for f in ['id','speaker','text','start','end']:
            if f not in ln: bad.append(f'{r["id"]}: line missing {f}')
        if ln.get('speaker') not in ('voice_src','voice_tgt','voice_src2','voice_tgt2'):
            bad.append(f'{r["id"]}: bad speaker {ln.get("speaker")}')
    # scenes structure
    for sc in r.get('scenes',[]):
        for f in ['scene_id','start_time','end_time','image_prompt','motion','audio_sync']:
            if f not in sc: bad.append(f'{r["id"]}: scene missing {f}')

print('ISSUES:', len(bad))
for b in bad: print('  -', b)

print('\n=== speaker<->language orientation check ===')
# voice_src/tgt map to language via prefix (ar-SA, zh-CN, en-US, es-ES)
LANG = {'ar-SA':'ar','zh-CN':'zh','en-US':'en','es-ES':'es'}
X2EN = ('arabic-to-english','chinese-to-english','spanish-to-english')
EN2X = ('english-to-arabic','english-to-chinese','english-to-spanish')
def nonlatin(s): return any(ord(c)>0x7F for c in s)
orient_issues = []
for r in reels:
    vm = {k:v for k,v in r.items() if k in ('voice_src','voice_tgt','voice_src2','voice_tgt2')}
    for ln in r['lines']:
        voice = vm.get(ln['speaker'],'')
        lang = LANG.get(voice[:5], '')
        txt = ln['text']
        is_en_gen = lang == 'en'
        # English generator -> text should be non-nonlatin (ascii); non-english -> text may be nonlatin
        if is_en_gen:
            if nonlatin(txt): orient_issues.append(f'{r["id"]}: {ln["speaker"]}(en) speaks non-latin text')
        else:
            # non-english voice; for ar/zh text should be nonlatin (but es is latin-ish)
            pass
print('ORIENTATION issues (en voice speaking non-latin):', len(orient_issues))
for o in orient_issues: print('  -', o)

print('\n=== numbering ===')
print('IDs currently:', sorted(set(x.split("-")[-1] for x in ids)), ' — NOTE: not 100+ yet (will renumber)')

print('\n=== top-level keys ===')
print(sorted(d.keys()))
