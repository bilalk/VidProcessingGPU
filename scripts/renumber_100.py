import json
CHANNELS = ['arabic-to-english','chinese-to-english','english-to-arabic',
            'english-to-chinese','english-to-spanish','spanish-to-english']
SRC = r'C:\ProjectComfy'
d = json.load(open(rf'{SRC}\test.json', encoding='utf-8'))
reels = d['reels']
nid = 100
for ch in CHANNELS:
    for r in reels:
        if r['channel'] == ch:
            r['id'] = f"{r['pair']}-{nid:03d}"
            r['seed'] = 51000 + (nid - 100)
            nid += 1
json.dump(d, open(rf'{SRC}\manifest_v2_100.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('done:', len(reels), 'reels')
for r in reels:
    print(' ', r['id'], r['pair'], r['topic'])
