# tts_v2.py - TTS for the NEW schema (lines[].speaker + text, words[4])
import json, os, subprocess, sys, time

ROOT = '/root/reels_r3'
TTS = os.path.join(ROOT, 'tts')
os.makedirs(TTS, exist_ok=True)
MAN = sys.argv[1] if len(sys.argv) > 1 else 'manifest_v2_100.json'
reels = json.load(open(os.path.join(ROOT, MAN), encoding='utf-8'))['reels']
ET = '/root/ComfyUI/venv/bin/edge-tts'

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

segs = []
for r in reels:
    rid = r['id']
    for ln in r['lines']:
        voice = r[ln['speaker']]
        segs.append((f"{rid}_L{ln['id']}", voice, ln['text']))
    w = r['words']
    segs.append((f"{rid}_w1", r['voice_src'], w[0]))
    segs.append((f"{rid}_w2", r['voice_src'], w[1]))
    segs.append((f"{rid}_w3", r['voice_tgt'], w[2]))
    segs.append((f"{rid}_w4", r['voice_tgt'], w[3]))

fails = []
for name, voice, text in segs:
    out = os.path.join(TTS, name + '.mp3')
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        log(f"skip {name}")
        continue
    res = subprocess.run([ET, '--voice', voice, '--rate=-10%', '--text', text,
                          '--write-media', out], capture_output=True)
    ok = os.path.exists(out) and os.path.getsize(out) > 2000
    log(f"{name} {'OK' if ok else 'FAIL'} ({voice})")
    if not ok:
        print(res.stderr.decode()[:300], flush=True)
        fails.append(name)

if fails:
    log(f"TTS_FAILS: {fails}")
    sys.exit(1)
log(f"TTS_ALL_DONE segments={len(segs)}")
