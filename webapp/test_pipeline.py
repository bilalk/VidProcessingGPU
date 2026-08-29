import json, sys
sys.path.insert(0, r'C:\ReelFactoryWeb')
import pipeline as P

for path in [r'C:\ProjectComfy\29Aug1.json', r'C:\ProjectComfy\reels\JSON_Aug28_1.json']:
    d = json.load(open(path, encoding='utf-8'))
    reels = d['reels']
    fmt = P.detect_format(reels)
    issues = P.validate(reels)
    print(f'== {path}')
    print(f'   reels={len(reels)}  format={fmt}  issues={len(issues)}')
    for i in issues[:3]:
        print('    ISSUE:', i)

# normalization (both)
a = json.load(open(r'C:\ProjectComfy\29Aug1.json', encoding='utf-8'))['reels']
fa = P.detect_format(a)
na = P.normalize(a, fa, 164)
print('\n== normalized 29aug first reel (ar-en-164) ==')
r = na[0]
print(' id=', r['id'], 'seed=', r['seed'], 'channel=', r['channel'])
print(' voice_src=', r['voice_src'], 'voice_tgt=', r['voice_tgt'])
print(' words[0]=', r['words'][0])
print(' narration[0]=', r['narration'][0][:60])
print(' scenes[0]=', r['scenes'][0][:80])

b = json.load(open(r'C:\ProjectComfy\reels\JSON_Aug28_1.json', encoding='utf-8'))['reels']
fb = P.detect_format(b)
nb = P.normalize(b, fb, 164)
print('\n== normalized aug28 first reel ==')
r = nb[0]
print(' id=', r['id'], 'channel=', r['channel'], 'pair=', r['pair'])
print(' voice_src=', r['voice_src'], 'voice_tgt=', r['voice_tgt'])
print(' words[0]=', r['words'][0])
print(' narration[0]=', r['narration'][0][:60])
print(' scenes[0]=', r['scenes'][0][:80])
print(' narration is english? nonlatin=', P.nonlatin(r['narration'][0]))

# dedup + id range
print('\n== dedup / id range ==')
used = P.collect_used_ids()
print(' max used id =', max(used) if used else 0)
print(' next start id =', P.find_next_start_id())
db = P.collect_past_topics()
print(' total past topics =', len(db))
red = P.check_dedup(a + b, db)
print(' redundant topics in the two samples =', len(red))
for x in red[:5]:
    print('   ', x['topic'])
