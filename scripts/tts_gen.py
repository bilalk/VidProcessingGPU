import json, os, subprocess, sys, time

ROOT = '/root/reels'
TTS = os.path.join(ROOT, 'tts')
os.makedirs(TTS, exist_ok=True)
reels = json.load(open(os.path.join(ROOT, 'manifest.json')))['reels']
ET = '/root/ComfyUI/venv/bin/edge-tts'

def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def speak_word(w):
    return w.capitalize() if w.isupper() and len(w) > 3 else w

segs = []
for r in reels:
    segs.append((r['id'] + '_1', r['voice_src'], r['sent_src']))
    segs.append((r['id'] + '_2', r['voice_tgt'], r['sent_tgt']))
    segs.append((r['id'] + '_3', r['voice_src'], speak_word(r['word_src'])))
    segs.append((r['id'] + '_4', r['voice_tgt'], speak_word(r['word_tgt'])))

fails = []
for name, voice, text in segs:
    out = os.path.join(TTS, name + '.mp3')
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        log(f"skip {name} (cached)")
        continue
    res = subprocess.run([ET, '--voice', voice, '--rate=-10%', '--text', text, '--write-media', out],
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
