import json

CHANNELS = ['arabic-to-english','chinese-to-english','english-to-arabic',
            'english-to-chinese','english-to-spanish','spanish-to-english']
SRC = r'C:\ProjectComfy\reels'

def renumber(src_file, dst_file, start_id):
    d = json.load(open(src_file, encoding='utf-8'))
    reels = d['reels']
    nid = start_id
    for ch in CHANNELS:
        for r in reels:
            if r['channel'] == ch:
                r['id'] = f"{r['pair']}-{nid:03d}"
                r['seed'] = 41001 + (nid - 25)
                nid += 1
    json.dump(d, open(dst_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ids = [r['id'] for r in reels]
    print(f'{dst_file}: {len(reels)} reels, ids {min(ids)}..{max(ids)}')

renumber(rf'{SRC}\JSON_Aug28_1.json', rf'{SRC}\manifest_aug28_g1.json', 59)
renumber(rf'{SRC}\JSON_Aug28_2.json', rf'{SRC}\manifest_aug28_g2.json', 71)
print('DONE')
