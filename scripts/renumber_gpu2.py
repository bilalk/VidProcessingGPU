import json

CHANNELS = ['arabic-to-english','chinese-to-english','english-to-arabic','english-to-chinese','english-to-spanish','spanish-to-english']

def renumber(src_file, dst_file, start_id):
    with open(src_file, encoding='utf-8') as f:
        d = json.load(f)
    reels = d['reels']
    nid = start_id
    for ch in CHANNELS:
        for r in reels:
            if r['channel'] == ch:
                r['id'] = f"{r['pair']}-{nid:03d}"
                r['seed'] = 41001 + (nid - 25)
                nid += 1
    with open(dst_file, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    ids = [r['id'] for r in reels]
    print(f'{dst_file}: {len(reels)} reels, IDs {min(ids)} to {max(ids)}')

renumber(r'D:\ProjectComfy\reels\gemini-code-1785895658171.json', r'D:\ProjectComfy\reels\r6_gpu2_w01.json', 31)
renumber(r'D:\ProjectComfy\reels\gemini-code-1785895723613.json', r'D:\ProjectComfy\reels\r6_gpu2_w02.json', 43)
print('DONE - 24 reels ready for GPU2')
