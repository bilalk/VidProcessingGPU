# tts_29.py - TTS for the 29Aug format: English narration (voice_tgt) + vocab terms (voice_src) + translations (voice_tgt)
import json, os, subprocess, sys, time

ROOT = '/root/reels_r3'
TTS = os.path.join(ROOT, 'tts')
os.makedirs(TTS, exist_ok=True)
MAN = sys.argv[1] if len(sys.argv) > 1 else 'manifest_29aug_g1.json'
reels = json.load(open(os.path.join(ROOT, MAN), encoding='utf-8'))['reels']
ET = '/root/ComfyUI/venv/bin/edge-tts'

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

segs = []
for r in reels:
    rid = r['id']
    ve = r['voice_tgt']   # English voice (normalized)
    vf = r['voice_src']   # Foreign voice (normalized)
    for k, line in enumerate(r['narration']):
        segs.append((f"{rid}_L{k+1}", ve, line))
    for j, w in enumerate(r['words']):
        segs.append((f"{rid}_w{j+1}", vf, w['src']))   # foreign term
        segs.append((f"{rid}_t{j+1}", ve, w['tgt']))   # english translation

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
