"""tts_gen3.py — TTS generator for R3 manifest schema (lines[] + words[]).
Adapted from tts_gen.py. Handles: 3 dialog lines × 2 voices + 3 words × 2 voices per reel.
Naming matches what assemble3.py expects: L1a, L1b, L2a, L2b, L3a, L3b, w1a, w1b, w2a, w2b, w3a, w3b.
"""
import json, os, subprocess, sys, time

ROOT = '/root/reels_r3'
TTS = os.path.join(ROOT, 'tts')
os.makedirs(TTS, exist_ok=True)
MAN = sys.argv[1] if len(sys.argv) > 1 else 'manifest_r3.json'
reels = json.load(open(os.path.join(ROOT, MAN), encoding='utf-8'))['reels']
ET = '/root/ComfyUI/venv/bin/edge-tts'


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def speak_word(w):
    return w.capitalize() if w.isupper() and len(w) > 3 else w


segs = []
for r in reels:
    rid = r['id']
    vs = r['voice_src']
    vt = r['voice_tgt']
    for k, line in enumerate(r['lines']):
        segs.append((f"{rid}_L{k+1}a", vs, line['src']))
        segs.append((f"{rid}_L{k+1}b", vt, line['tgt']))
    for j, w in enumerate(r['words']):
        segs.append((f"{rid}_w{j+1}a", vs, speak_word(w['src'])))
        segs.append((f"{rid}_w{j+1}b", vt, speak_word(w['tgt'])))

fails = []
for name, voice, text in segs:
    out = os.path.join(TTS, name + '.mp3')
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        log(f"skip {name} (cached)")
        continue
    res = subprocess.run(
        [ET, '--voice', voice, '--rate=-10%', '--text', text, '--write-media', out],
        capture_output=True)
    ok = os.path.exists(out) and os.path.getsize(out) > 2000
    log(f"{name} {'OK' if ok else 'FAIL'} ({voice})")
    if not ok:
        print(res.stderr.decode()[:400], flush=True)
        fails.append(name)

if fails:
    log(f"TTS_FAILS: {fails}")
    sys.exit(1)
log(f"TTS_ALL_DONE segments={len(segs)}")
