import json, os, subprocess, sys, time, concurrent.futures

ROOT = '/root/reels'
reels = json.load(open(os.path.join(ROOT, 'manifest.json')))['reels']

FONTS = {'en': 'Noto Sans', 'es': 'Noto Sans', 'zh': 'Noto Sans CJK SC', 'ar': 'Noto Naskh Arabic'}

def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def lang_of(voice):
    return voice.split('-')[0]

def esc(t):
    return t.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')

def ts(s):
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"

def make_ass(r):
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
    ev = []
    ev.append(f"Dialogue: 0,{ts(0.2)},{ts(7.0)},Src,,0,0,0,,{esc(r['sent_src'])}")
    ev.append(f"Dialogue: 0,{ts(7.2)},{ts(14.0)},Tgt,,0,0,0,,{esc(r['sent_tgt'])}")
    if r['sent_translit']:
        ev.append(f"Dialogue: 0,{ts(7.2)},{ts(14.0)},Tr,,0,0,0,,{esc(r['sent_translit'])}")
    wtop = r['word_src'].title() if ls == 'en' else r['word_src']
    ev.append(f"Dialogue: 0,{ts(14.2)},{ts(21.3)},Src,,0,0,0,,{esc(wtop)}")
    wb = r['word_tgt'] if lt != 'en' else r['word_tgt'].title()
    if r['word_translit']:
        wb = wb + "  (" + r['word_translit'] + ")"
    ev.append(f"Dialogue: 0,{ts(14.2)},{ts(21.3)},Tgt,,0,0,0,,{esc(wb)}")
    return head + "\n".join(ev) + "\n"

ZOOMS = [
    "zoompan=z='min(1.0+0.0006*on,1.13)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=210:s=1080x1920:fps=30",
    "zoompan=z='max(1.13-0.0006*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=210:s=1080x1920:fps=30",
    "zoompan=z='1.09':x='(iw-iw/zoom)*on/210':y='ih/2-(ih/zoom/2)':d=210:s=1080x1920:fps=30",
]

def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError('CMD FAIL: ' + cmd[0] + ' :: ' + p.stderr.decode()[-350:])

def build_seg(img, out, zx):
    vf = f"scale=1536:2688:force_original_aspect_ratio=increase,crop=1536:2688,{zx}"
    run(['ffmpeg', '-y', '-loop', '1', '-i', img, '-vf', vf, '-frames:v', '210',
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', out])


def build_reel(r):
    rid = r['id']
    d = os.path.join(ROOT, 'build', rid)
    os.makedirs(d, exist_ok=True)
    assp = os.path.join(d, rid + '.ass')
    with open(assp, 'w', encoding='utf-8') as f:
        f.write(make_ass(r))
    segs = []
    for k in range(3):
        img = os.path.join(ROOT, 'img', f"{rid}_s{k+1}.png")
        seg = os.path.join(d, f"seg{k+1}.mp4")
        if not (os.path.exists(seg) and os.path.getsize(seg) > 100000):
            build_seg(img, seg, ZOOMS[k])
        segs.append(seg)
    lst = os.path.join(d, 'segs.txt')
    with open(lst, 'w') as f:
        f.write("".join(f"file '{s}'\n" for s in segs))
    vsub = os.path.join(d, 'vsub.mp4')
    run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
         '-vf', f"ass={assp}", '-c:v', 'libx264', '-preset', 'veryfast',
         '-crf', '19', '-pix_fmt', 'yuv420p', vsub])
    out = os.path.join(ROOT, 'out', r['channel'], rid + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    t = lambda k: os.path.join(ROOT, 'tts', f"{rid}_{k}.mp3")
    fc = ("[1]adelay=300|300[a1];[2]adelay=7200|7200[a2];[3]adelay=14300|14300[a3];"
          "[4]adelay=17200|17200[a4];[5]volume=0.13[mus];"
          "[a1][a2][a3][a4][mus]amix=inputs=5:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    run(['ffmpeg', '-y', '-i', vsub, '-i', t(1), '-i', t(2), '-i', t(3), '-i', t(4),
         '-stream_loop', '-1', '-i', os.path.join(ROOT, 'bed.wav'),
         '-filter_complex', fc, '-map', '0:v', '-map', '[a]',
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-t', '21.4',
         '-movflags', '+faststart', out])
    return rid, out

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
                rid, out = fut.result()
                results[rid] = ('OK', out)
                log(f"{rid} ASSEMBLED")
            except Exception as e:
                results[rid] = ('FAIL', str(e))
                log(f"{rid} FAIL: {str(e)[:200]}")
    print("\n===== QA REPORT =====", flush=True)
    okc = 0
    for r in reels:
        rid = r['id']
        st, val = results.get(rid, ('MISSING', ''))
        if st == 'OK':
            print(f"PASS {rid}: {qa(val)}", flush=True)
            okc += 1
        else:
            print(f"FAIL {rid}: {val[:150]}", flush=True)
    log(f"ASSEMBLE_SUMMARY ok={okc}/{len(reels)} total={int(time.time()-t0)}s")
    if okc < len(reels):
        sys.exit(1)

if __name__ == '__main__':
    main()
