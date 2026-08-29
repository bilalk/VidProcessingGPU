import sys, json
sys.path.insert(0, r'C:\ReelFactoryWeb')
import pipeline as P
import gpu as G

files = [r'C:\ReelFactoryWeb\uploads\20260829-003903_a_aug30Json1.json',
         r'C:\ReelFactoryWeb\uploads\20260829-003903_b_aug30Json2.json']
db = P.collect_past_topics()
print('=== topic / dedup check ===')
for f in files:
    d = json.load(open(f, encoding='utf-8'))
    print('FILE', f.split('\\')[-1], f"({len(d['reels'])} reels)")
    for r in d['reels']:
        t = r.get('topic')
        print('   ', 'REDUNDANT' if t in db else 'NEW     ', ':', t)
print('total past topics in DB:', len(db))

print('\n=== server state ===')
g = G.GPU('129.212.190.223', r'C:\Users\tester\.ssh\id_newgpu', 'root').connect()
print('pipeline_running      =', g.pipeline_running())
c, o, e = g.run("ls /root/reels_r3/manifest_web_*.json /root/reels_r3/web_flux.sh 2>&1 | head")
print('web manifests pushed  :', o.strip() or '(none)')
c, o, e = g.run("ls /root/reels_ltx29/out_mobile/*/*.mp4 2>/dev/null | wc -l")
print('LTX out_mobile count  :', o.strip())
c, o, e = g.run("ps aux | grep -E 'tts_29|flux_gen|assemble_29|ltx_29' | grep -v grep")
print('running pipeline procs:')
print(o.strip() or '  (none)')
g.close()
