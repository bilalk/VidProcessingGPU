# assemble5.py — R3 workspace version of assemble3.py (points to /root/reels_r3/).
# 4-panel format with recap card, timeline from real TTS durations, 5-lane parallel.
import json, os, subprocess, sys, time, concurrent.futures

ROOT = '/root/reels_r3'
MAN = sys.argv[1] if len(sys.argv) > 1 else 'manifest_r3.json'
with open(os.path.join(ROOT, MAN), encoding='utf-8') as fh:
    reels = json.load(fh)['reels']

FONTS = {'en': 'Noto Sans', 'es': 'Noto Sans', 'zh': 'Noto Sans CJK SC', 'ar': 'Noto Naskh Arabic'}
FPS = 30
LEAD = 0.35
GAP = 0.30
TAIL = 0.55
MINPANEL = 7.5
RECAP = 3.4

def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def lang_of(v):
    return v.split('-')[0]

def esc(t):
    return t.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')

def ts(s):
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"

_durc = {}
def dur(p):
    if p not in _durc:
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                            '-of', 'csv=p=0', p], capture_output=True)
        _durc[p] = float(r.stdout.decode().strip())
    return _durc[p]

def tp(rid, name):
    return os.path.join(ROOT, 'tts', f"{rid}_{name}.mp3")

def build_timeline(r):
    rid = r['id']
    ls = lang_of(r['voice_src']); lt = lang_of(r['voice_tgt'])
    ev = []; audio = []; panels = []
    cur = 0.0
    for k, line in enumerate(r['lines']):
        pstart = cur
        pa = tp(rid, f"L{k+1}a"); da = dur(pa)
        pb = tp(rid, f"L{k+1}b"); db = dur(pb)
        s0 = cur + LEAD
        t0 = s0 + da + GAP
        audio.append((pa, int(round(s0 * 1000))))
        audio.append((pb, int(round(t0 * 1000))))
        pend = max(pstart + MINPANEL, t0 + db + TAIL)
        ev.append((s0 - 0.05, min(s0 + da + 0.25, pend - 0.1), 'Src', line['src']))
        ev.append((t0 - 0.05, pend - 0.15, 'Tgt', line['tgt']))
        if line.get('translit'):
            ev.append((t0 - 0.05, pend - 0.15, 'Tr', line['translit']))
        panels.append((pstart, pend, k))
        cur = pend
    pstart = cur
    wcur = cur + LEAD
    for j, w in enumerate(r['words']):
        pa = tp(rid, f"w{j+1}a"); da = dur(pa)
        pb = tp(rid, f"w{j+1}b"); db = dur(pb)
        s0 = wcur; t0 = s0 + da + GAP; wend = t0 + db
        audio.append((pa, int(round(s0 * 1000))))
        audio.append((pb, int(round(t0 * 1000))))
        wt = w['src'].title() if ls == 'en' else w['src']
        wb = w['tgt'].title() if lt == 'en' else w['tgt']
        if w.get('translit'):
            wb = wb + "  (" + w['translit'] + ")"
        ev.append((s0 - 0.05, wend + 0.30, 'Src', wt))
        ev.append((s0 - 0.05, wend + 0.30, 'Tgt', wb))
        wcur = wend + 0.45
    rstart = wcur + 0.35
    rend = rstart + RECAP
    ys = {1: [960], 2: [860, 1120], 3: [700, 960, 1220]}[len(r['words'])]
    for j, w in enumerate(r['words']):
        wt = w['src'].title() if ls == 'en' else w['src']
        wb = w['tgt'].title() if lt == 'en' else w['tgt']
        if w.get('translit'):
            wb = wb + "  (" + w['translit'] + ")"
        y = ys[j]
        ev.append((rstart, rend, 'Src', '{\\pos(540,%d)}' % y + wt))
        ev.append((rstart, rend, 'Tgt', '{\\pos(540,%d)}' % (y + 64) + wb))
    pend = max(pstart + MINPANEL, wcur + 0.25, rend + 0.35)
    panels.append((pstart, pend, 3))
    cur = pend
    return panels, ev, audio, cur

def make_ass(r, ev):
    ls = lang_of(r['voice_src']); lt = lang_of(r['voice_tgt'])
    fs = FONTS.get(ls, 'Noto Sans'); ft = FONTS.get(lt, 'Noto Sans')
    head = (
        "[Script Info]\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Src,{fs},56,&H00FFFFFF,&H00FFFFFF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,8,70,70,170,1\n"
        f"Style: Tgt,{ft},62,&H0000D7FF,&H0000D7FF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,2,70,70,330,1\n"
        f"Style: Tr,{ft},38,&H00E8E8E8,&H00E8E8E8,&H90000000,&H90000000,0,2,0,0,100,100,0,0,1,2.5,1,2,70,70,210,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    for (a, b, st, txt) in ev:
        body = txt if txt.startswith('{\\pos(') else esc(txt)
        lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},{st},,0,0,0,,{body}")
    return head + "\n".join(lines) + "\n"

ZOOMS = [
    "zoompan=z='min(1.0+0.0006*on,1.13)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30",
    "zoompan=z='max(1.13-0.0006*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30",
    "zoompan=z='1.09':x='(iw-iw/zoom)*on/{n}':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30",
    "zoompan=z='1.09':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/{n}':d={n}:s=1080x1920:fps=30",
]

def run_cmd(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError('CMD FAIL: ' + cmd[0] + ' :: ' + p.stderr.decode()[-350:])

def build_seg(img, out, zx, frames):
    vf = f"scale=1536:2688:force_original_aspect_ratio=increase,crop=1536:2688,{zx}"
    run_cmd(['ffmpeg', '-y', '-loop', '1', '-i', img, '-vf', vf, '-frames:v', str(frames),
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', out])

def build_reel(r):
    rid = r['id']
    d = os.path.join(ROOT, 'build', rid)
    os.makedirs(d, exist_ok=True)
    panels, ev, audio, total = build_timeline(r)
    assp = os.path.join(d, rid + '.ass')
    with open(assp, 'w', encoding='utf-8') as f:
        f.write(make_ass(r, ev))
    segs = []
    for (pstart, pend, k) in panels:
        frames = max(30, int(round((pend - pstart) * FPS)))
        img = os.path.join(ROOT, 'img', f"{rid}_s{k+1}.png")
        seg = os.path.join(d, f"seg{k+1}.mp4")
        if not (os.path.exists(seg) and os.path.getsize(seg) > 100000):
            build_seg(img, seg, ZOOMS[k].format(n=frames), frames)
        segs.append(seg)
    lst = os.path.join(d, 'segs.txt')
    with open(lst, 'w') as f:
        f.write("".join(f"file '{s}'\n" for s in segs))
    vsub = os.path.join(d, 'vsub.mp4')
    run_cmd(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
         '-vf', f"ass={assp}", '-c:v', 'libx264', '-preset', 'veryfast',
         '-crf', '19', '-pix_fmt', 'yuv420p', vsub])
    out = os.path.join(ROOT, 'out', r['channel'], rid + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = len(audio)
    fc = "".join(f"[{i+1}]adelay={ms}|{ms}[a{i}];" for i, (p, ms) in enumerate(audio))
    fc += f"[{n+1}]volume=0.13[mus];"
    fc += "".join(f"[a{i}]" for i in range(n))
    fc += "[mus]amix=inputs=%d:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]" % (n + 1)
    cmd = ['ffmpeg', '-y', '-i', vsub]
    for (p, ms) in audio:
        cmd += ['-i', p]
    cmd += ['-stream_loop', '-1', '-i', os.path.join(ROOT, 'bed.wav'),
            '-filter_complex', fc, '-map', '0:v', '-map', '[a]',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '160k', '-t', f"{total:.2f}",
            '-movflags', '+faststart', out]
    run_cmd(cmd)
    # export script.txt
    sp = os.path.join(ROOT, 'out', r['channel'], rid + '.script.txt')
    with open(sp, 'w', encoding='utf-8') as f:
        f.write(f"TITLE: {r['id']} | {r['topic']}\nCHANNEL: {r['channel']} | PAIR: {r['pair']}\n\n=== WORDS ===\n")
        for w in r['words']:
            f.write(f"{w['src']} = {w['tgt']}")
            if w.get('translit'): f.write(f" ({w['translit']})")
            f.write("\n")
        f.write("\n=== DIALOG ===\n")
        for ln in r['lines']:
            f.write(f"SRC: {ln['src']}\nTGT: {ln['tgt']}")
            if ln.get('translit'): f.write(f"\nTRL: {ln['translit']}")
            f.write("\n\n")
        f.write(f"\n=== SCENES ===\n")
        for i, s in enumerate(r['scenes']):
            f.write(f"Scene {i+1}: {s}\n")
    # copy .ass to output
    import shutil
    shutil.copy(assp, os.path.join(ROOT, 'out', r['channel'], rid + '.ass'))
    return rid, out, total

def qa(out):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'format=duration', '-show_entries',
                        'stream=codec_name,width,height',
                        '-of', 'csv=p=0', out], capture_output=True)
    return p.stdout.decode().strip().replace('\n', ' | ')

def main():
    t0 = time.time()
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(build_reel, r): r['id'] for r in reels}
        for fut in concurrent.futures.as_completed(futs):
            rid = futs[fut]
            try:
                rid, out, total = fut.result()
                results[rid] = ('OK', out)
                log(f"{rid} ASSEMBLED ({total:.1f}s)")
            except Exception as e:
                results[rid] = ('FAIL', str(e))
                log(f"{rid} FAIL: {str(e)[:200]}")
    print("\n===== QA REPORT R3 =====", flush=True)
    okc = 0
    for r in reels:
        rid = r['id']
        st, val = results.get(rid, ('MISSING', ''))
        if st == 'OK':
            info = qa(val)
            dsec = 0.0
            for tok in info.split(' | '):
                try:
                    dsec = max(dsec, float(tok))
                except Exception:
                    pass
            if dsec >= 29.5 and 'aac' in info:
                print(f"PASS {rid}: {info}", flush=True)
                okc += 1
            else:
                print(f"FAIL {rid}: bad duration/audio :: {info}", flush=True)
        else:
            print(f"FAIL {rid}: {val[:150]}", flush=True)
    log(f"ASSEMBLE5_SUMMARY ok={okc}/{len(reels)} total={int(time.time()-t0)}s")
    if okc < len(reels):
        sys.exit(1)

if __name__ == '__main__':
    main()
