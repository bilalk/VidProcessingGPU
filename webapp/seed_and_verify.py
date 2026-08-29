import sys, json, os
sys.path.insert(0, r'C:\ReelFactoryWeb')
import pipeline as P
import gpu as G

# 1. seed used_topics.json from PAST json (excluding the new aug30 files)
used = P.collect_past_topics(exclude={'aug30Json1.json', 'aug30Json2.json'})
os.makedirs(r'C:\ReelFactoryWeb\state', exist_ok=True)
json.dump(sorted(used), open(r'C:\ReelFactoryWeb\state\used_topics.json', 'w'), indent=2)
print('seeded used_topics.json:', len(used), 'topics')

# 2. verify aug30 is NOT flagged redundant now
reels = (json.load(open(r'C:\ProjectComfy\aug30Json1.json', encoding='utf-8'))['reels']
         + json.load(open(r'C:\ProjectComfy\aug30Json2.json', encoding='utf-8'))['reels'])
redup = P.check_dedup(reels, used)
print('aug30 redundant count =', len(redup), '(want 0)')

# 3. verify pipeline_running now returns False (pipeline actually done)
g = G.GPU('129.212.190.223', r'C:\Users\tester\.ssh\id_newgpu', 'root').connect()
print('pipeline_running =', g.pipeline_running(), '(want False)')
g.close()
