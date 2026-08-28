import json

CHANNELS = ['english-to-arabic', 'english-to-chinese', 'english-to-spanish']
SRC = r'C:\ProjectComfy\reels'

for name in ['manifest_aug28_g1.json', 'manifest_aug28_g2.json']:
    p = rf'{SRC}\{name}'
    d = json.load(open(p, encoding='utf-8'))
    cnt = 0
    for r in d['reels']:
        if r['channel'] in CHANNELS:
            for ln in r['lines']:
                ln['src'], ln['tgt'] = ln['tgt'], ln['src']
                cnt += 1
            for w in r['words']:
                w['src'], w['tgt'] = w['tgt'], w['src']
                cnt += 1
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{name}: swapped {cnt} src/tgt pairs')
print('DONE')
