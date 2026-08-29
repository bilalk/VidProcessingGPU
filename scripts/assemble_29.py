# assemble_29.py - 4-panel ~60s assembly for 29Aug format (English narration + bilingual vocab)
import json, os, subprocess, sys, time

ROOT = '/root/reels_r3'
OUT = os.path.join(ROOT, 'out_29aug')
BUILD = os.path.join(ROOT, 'build_29aug')
TTS = os.path.join(ROOT, 'tts')
IMG = os.path.join(ROOT, 'img')
os.makedirs(OUT, exist_ok=True); os.makedirs(BUILD, exist_ok=True)
MAN = sys.argv[1] if len(sys.argv) > 1 else 'manifest_29aug_g1.json'
reels = json.load(open(os.path.join(ROOT, MAN), encoding='utf-8'))['reels']
BED = os.path.join(ROOT, 'bed.wav')
FPS = 30
LEAD = 0.4; GAP = 0.5; TAIL = 0.9; MINPANEL = 11.0; RECAP = 13.0
FONTS = {'ar':'Noto Naskh Arabic','zh':'Noto Sans CJK SC','es':'Noto Sans','en':'Noto Sans'}

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def lang_of(v): return v.split('-')[0]
def esc(t): return t.replace('\\','\\\\').replace('{','\\{').replace('}','\\}')
def ts(s):
    h=int(s//3600); m=int((s%3600)//60); sec=s%60
    return f"{h}:{m:02d}:{sec:05.2f}"
def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError('CMD FAIL ' + cmd[0] + ' :: ' + p.stderr.decode()[-300:])
def dur(p):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p], capture_output=True)
    return float(r.stdout.decode().strip())

ZOOMS = [
    "zoompan=z='min(1.0+0.0007*on,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30",
    "zoompan=z='max(1.15-0.0007*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30",
    "zoompan=z='1.10':x='(iw-iw/zoom)*on/{n}':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30",
    "zoompan=z='1.10':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/{n}':d={n}:s=1080x1920:fps=30",
]

def make_ass(r, ev):
    fs = FONTS.get(lang_of(r['voice_src']), 'Noto Sans')
    ft = FONTS.get(lang_of(r['voice_tgt']), 'Noto Sans')
    head = ("[Script Info]\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Src,{fs},56,&H00FFFFFF,&H00FFFFFF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,8,70,70,170,1\n"
            f"Style: Tgt,{ft},62,&H0000D7FF,&H0000D7FF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,2,70,70,330,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = [f"Dialogue: 0,{ts(a)},{ts(b)},{st},,0,0,0,,{esc(txt)}" for a,b,st,txt in ev]
    return head + "\n".join(lines) + "\n"

def build_timeline(r):
    rid = r['id']
    ev = []; audio = []; panels = []; cur = 0.0
    for k in range(3):
        nk = dur(os.path.join(TTS, f"{rid}_L{k+1}.mp3"))
        pstart = cur; s0 = cur + LEAD
        pend = max(pstart + MINPANEL, s0 + nk + TAIL)
        audio.append((os.path.join(TTS, f"{rid}_L{k+1}.mp3"), int(round(s0*1000))))
        ev.append((s0-0.05, pend-0.1, 'Tgt', r['narration'][k]))
        panels.append((pstart, pend, k)); cur = pend
    pstart = cur; wcur = cur + LEAD
    for j, w in enumerate(r['words']):
        fk = dur(os.path.join(TTS, f"{rid}_w{j+1}.mp3")); tk = dur(os.path.join(TTS, f"{rid}_t{j+1}.mp3"))
        s0 = wcur
        audio.append((os.path.join(TTS, f"{rid}_w{j+1}.mp3"), int(round(s0*1000))))
        audio.append((os.path.join(TTS, f"{rid}_t{j+1}.mp3"), int(round((s0+fk+0.15)*1000))))
        ev.append((s0-0.05, s0+fk+tk+0.8, 'Src', w['src']))
        ev.append((s0-0.05, s0+fk+tk+0.8, 'Tgt', w['tgt']))
        wcur = s0 + fk + tk + 0.6
    pend = max(pstart + RECAP, wcur + 0.5)
    panels.append((pstart, pend, 3))
    return panels, ev, audio, pend

for r in reels:
    rid = r['id']
    panels, ev, audio, total = build_timeline(r)
    d = os.path.join(BUILD, rid); os.makedirs(d, exist_ok=True)
    segs = []
    for i,(pstart,pend,k) in enumerate(panels):
        frames = max(30, int(round((pend-pstart)*FPS)))
        seg = os.path.join(d, f"seg{k+1}.mp4")
        img = os.path.join(IMG, f"{rid}_s{k+1}.png")
        vf = f"scale=1536:2688:force_original_aspect_ratio=increase,crop=1536:2688,{ZOOMS[k].format(n=frames)}"
        run(['ffmpeg','-y','-loop','1','-i',img,'-vf',vf,'-frames:v',str(frames),
             '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p', seg])
        segs.append(seg)
    lst = os.path.join(d,'segs.txt')
    open(lst,'w').write("".join(f"file '{s}'\n" for s in segs))
    vsub = os.path.join(d,'vsub.mp4')
    assp = os.path.join(d, rid + '.ass')
    open(assp,'w',encoding='utf-8').write(make_ass(r, ev))
    run(['ffmpeg','-y','-f','concat','-safe','0','-i',lst,'-vf',f'ass={assp}',
         '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p', vsub])
    out = os.path.join(OUT, r['channel'], rid + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = len(audio)
    fc = "".join(f"[{i+1}]adelay={ms}|{ms}[a{i}];" for i,(p,ms) in enumerate(audio))
    fc += f"[{n+1}]volume=0.13[mus];" + "".join(f"[a{i}]" for i in range(n))
    fc += f"[mus]amix=inputs={n+1}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    cmd = ['ffmpeg','-y','-i',vsub]
    for (p,ms) in audio: cmd += ['-i', p]
    cmd += ['-stream_loop','-1','-i',BED,'-filter_complex',fc,'-map','0:v','-map','[a]',
            '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
            '-c:a','aac','-b:a','160k','-t',f"{total:.2f}",'-movflags','+faststart', out]
    run(cmd)
    log(f"DONE {rid} dur={total:.1f}s -> out_29aug/{r['channel']}/{rid}.mp4")

log(f"ASSEMBLE_29_ALL_DONE {len(reels)} reels")
