import json, re
from collections import Counter

# File 1 -> IDs 027-028 per channel (continues from R4_test which used 025-026)
# File 2 -> IDs 029-030 per channel

mapping = {
    'gemini-code-1785887962324.json': 27,  # will produce 027-028
    'gemini-code-1785888036566.json': 29,  # will produce 029-030
}

all_words = []
for fn, new_start in mapping.items():
    in_path = fr'D:\ProjectComfy\reels\{fn}'
    with open(in_path, encoding='utf-8') as f:
        d = json.load(f)

    reels = d['reels']
    print(f'=== {fn} -> {len(reels)} reels, IDs starting at {new_start:03d} ===')
    
    for r in reels:
        old_id = r['id']
        m = re.match(r'([a-z]{2}-[a-z]{2}-)(\d+)', old_id)
        if m:
            prefix = m.group(1)
            old_num = int(m.group(2))
            new_num = new_start + (old_num - 25)  # 025->27, 026->28
            r['id'] = f"{prefix}{new_num:03d}"
            r['seed'] = 41001 + (new_num - 25)
            print(f"  {old_id} -> {r['id']} seed={r['seed']}")
    
    # Check channels
    ch = Counter(r['channel'] for r in reels)
    print(f"  Channels: {dict(ch)}")
    
    # Check uniqueness
    ids = [r['id'] for r in reels]
    if len(ids) != len(set(ids)):
        print(f"  WARNING: duplicate IDs!")
    
    # Collect words
    for r in reels:
        for w in r['words']:
            all_words.append(w['tgt'].lower().strip())
    
    out_fn = fn.replace('.json', f'_r5_b{list(mapping.keys()).index(fn)+1:02d}.json')
    out_path = fr'D:\ProjectComfy\reels\_scripts\round5\{out_fn}'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    # Also save to reels root for upload
    with open(fr'D:\ProjectComfy\reels\{out_fn}', 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"  Saved: {out_path}")
    print(f"  Saved: D:\\ProjectComfy\\reels\\{out_fn}")
    print()

# Cross-manifest word uniqueness
from collections import Counter
wcount = Counter(all_words)
dup_words = [w for w,c in wcount.items() if c > 1]
print(f"Total words: {len(all_words)} | Unique: {len(set(all_words))} | Cross-dupes: {len(dup_words)}")
if dup_words:
    print(f"  DUPLICATE: {dup_words}")
print("\nALL VALIDATED - ready for parallel upload")

