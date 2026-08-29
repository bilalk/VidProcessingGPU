import json
CHANNELS = ['arabic-to-english','chinese-to-english','english-to-arabic',
            'english-to-chinese','english-to-spanish','spanish-to-english']
EN2X = ('english-to-arabic','english-to-chinese','english-to-spanish')
SRC = r'C:\ProjectComfy'

def renumber_transform(src, dst, start):
    d = json.load(open(rf'{SRC}\{src}', encoding='utf-8'))
    nid = start
    for ch in CHANNELS:
        for r in d['reels']:
            if r['channel'] != ch:
                continue
            r['id'] = f"{r['pair']}-{nid:03d}"
            r['seed'] = 62000 + (nid - 140)
            nid += 1
            # words: term/translation -> src/tgt (term stays foreign, translation=english)
            for w in r['words']:
                w['src'] = w.pop('term')
                w['tgt'] = w.pop('translation')
            # narration: keep 3 english strings
            r['narration'] = list(r['lines'])
            r.pop('lines', None)
            # scenes: object -> single prompt string (prompt + LTX motion profile)
            r['scenes'] = [f"{s['prompt']}, LTX motion: {s['ltx_motion_profile']}" for s in r['scenes']]
            # normalize voices so voice_src = FOREIGN language, voice_tgt = ENGLISH
            if r['channel'] in EN2X:
                r['voice_src'], r['voice_tgt'] = r['voice_tgt'], r['voice_src']
                r['voice_src2'], r['voice_tgt2'] = r['voice_tgt2'], r['voice_src2']
    json.dump(d, open(rf'{SRC}\{dst}', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{dst}: {len(d["reels"])} reels')

renumber_transform('29Aug1.json', 'manifest_29aug_g1.json', 140)
renumber_transform('29Aug2.json', 'manifest_29aug_g2.json', 152)
print('DONE')
