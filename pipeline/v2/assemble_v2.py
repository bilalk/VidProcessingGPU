# assemble_v2.py - assemble NEW schema (single scene + 2 dialogue lines + 4-word recap)
import json, os, subprocess, sys, time

ROOT = '/root/reels_r3'
OUT = os.path.join(ROOT, 'out_v2_100')
BUILD = os.path.join(ROOT, 'build_v2_100')
os.makedirs(OUT, exist_ok=True)
os.makedirs(BUILD, exist_ok=True)
MAN = sys.argv[1] if len(sys.argv) > 1 else 'manifest_v2_100.json'
reels = json.load(open(os.path.join(ROOT, MAN), encoding='utf-8'))['reels']
BED = os.path.join(ROOT, 'bed.wav')
FPS = 30
RECAP = 2.0

FONTS = {'ar': 'Noto Naskh Arabic', 'zh': 'Noto Sans CJK SC', 'es': 'Noto Sans',
         'en': 'Noto Sans', 'it': 'Noto Sans', 'de': 'Noto Sans', 'hi': 'Noto Sans Devanagari'}

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def lang_of(v): return v.split('-')[0]
def esc(t): return t.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
def ts(s):
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"

def make_ass(r, dur):
    rid = r['id']
    fs = FONTS.get(lang_of(r['voice_src']), 'Noto Sans')
    ft = FONTS.get(lang_of(r['voice_tgt']), 'Noto Sans')
    head = ("[Script Info]\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Src,{fs},56,&H00FFFFFF,&H00FFFFFF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,8,70,70,170,1\n"
            f"Style: Tgt,{ft},62,&H0000D7FF,&H0000D7FF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,2,70,70,330,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ev = []
    for ln in r['lines']:
        style = 'Src' if ln['speaker'].startswith('voice_src') else 'Tgt'
        ev.append(f"Dialogue: 0,{ts(ln['start'])},{ts(ln['end'])},{style},,0,0,0,,{esc(ln['text'])}")
    # vocab recap (last RECAP seconds)
    ws = r['words']; rs = dur - RECAP
    ev.append(f"Dialogue: 0,{ts(rs)},{ts(dur)},Src,,0,0,0,,{esc(ws[0] + '   ' + ws[1])}")
    ev.append(f"Dialogue: 0,{ts(rs)},{ts(dur)},Tgt,,0,0,0,,{esc(ws[2] + '   ' + ws[3])}")
    return head + "\n".join(ev) + "\n"

def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError('CMD FAIL ' + cmd[0] + ' :: ' + p.stderr.decode()[-350:])

def get_dur(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', p], capture_output=True)
    return float(r.stdout.decode().strip())

for r in reels:
    rid = r['id']
    sc = r['scenes'][0]
    dur = sc['end_time'] + RECAP
    frames = int(round(dur * FPS))
    d = os.path.join(BUILD, rid)
    os.makedirs(d, exist_ok=True)
    img = os.path.join(ROOT, 'img', f"{rid}_s1.png")
    seg = os.path.join(d, 'seg.mp4')
    vf = ("scale=1536:2688:force_original_aspect_ratio=increase,crop=1536:2688,"
          f"zoompan=z='min(1.0+0.0006*on,1.13)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={FPS}")
    run(['ffmpeg', '-y', '-loop', '1', '-i', img, '-vf', vf, '-frames:v', str(frames),
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', seg])

    assp = os.path.join(d, rid + '.ass')
    open(assp, 'w', encoding='utf-8').write(make_ass(r, dur))
    vsub = os.path.join(d, 'vsub.mp4')
    run(['ffmpeg', '-y', '-i', seg, '-vf', f'ass={assp}', '-c:v', 'libx264',
         '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', vsub])

    out = os.path.join(OUT, r['channel'], rid + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    L1 = os.path.join(ROOT, 'tts', f"{rid}_L1.mp3")
    L2 = os.path.join(ROOT, 'tts', f"{rid}_L2.mp3")
    d1 = int(round(r['lines'][0]['start'] * 1000))
    d2 = int(round(r['lines'][1]['start'] * 1000))
    fc = (f"[1]adelay={d1}|{d1}[a1];[2]adelay={d2}|{d2}[a2];[3]volume=0.13[mus];"
          "[a1][a2][mus]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    run(['ffmpeg', '-y', '-i', vsub, '-i', L1, '-i', L2, '-stream_loop', '-1', '-i', BED,
         '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'libx264',
         '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
         '-b:a', '160k', '-t', f"{dur:.2f}", '-movflags', '+faststart', out])
    log(f"DONE {rid} dur={dur:.1f}s -> out/{r['channel']}/{rid}.mp4")

log(f"ASSEMBLE_V2_ALL_DONE {len(reels)} reels")
