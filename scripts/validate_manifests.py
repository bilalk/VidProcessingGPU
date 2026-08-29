import json, collections, sys

for fn in sys.argv[1:]:
    with open(fn, encoding='utf-8') as f:
        d = json.load(f)
    reels = d['reels']
    print(f'=== {fn} ===')
    print(f'Count: {len(reels)}')
    print(f'IDs: {[r["id"] for r in reels]}')
    ch = collections.Counter(r['channel'] for r in reels)
    print(f'Channels: {dict(ch)}')
    all_w = [w['tgt'].lower() for r in reels for w in r['words']]
    dups = [x for x,c in collections.Counter(all_w).items() if c>1]
    print(f'Word dupes: {dups if dups else "NONE"} ({len(set(all_w))} unique)')
    errs = []
    for r in reels:
        for k in ['id','channel','pair','topic','seed','voice_src','voice_tgt','words','lines','scenes']:
            if k not in r: errs.append(f'{r.get("id","?")}: missing {k}')
        if len(r.get('words',[])) != 3: errs.append(f'{r["id"]}: words={len(r.get("words",[]))}')
        if len(r.get('lines',[])) != 3: errs.append(f'{r["id"]}: lines={len(r.get("lines",[]))}')
        if len(r.get('scenes',[])) != 4: errs.append(f'{r["id"]}: scenes={len(r.get("scenes",[]))}')
    print(f'Errors: {errs if errs else "NONE"}')
    # Check if IDs continue from 024/026
    ids = [r['id'] for r in reels]
    print(f'ID range: {min(ids)} to {max(ids)}')
    print()
    if errs:
        sys.exit(1)
print('ALL PASS')
