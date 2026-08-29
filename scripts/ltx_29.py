# ltx_29.py - LTX-2.3 FLF (4-panel) for the 29Aug "narration + vocab" schema. Mobile + desktop.
import json, os, sys, time, subprocess, shutil, urllib.request, urllib.parse, concurrent.futures

BASE = "http://127.0.0.1:8188"
CKPT = "ltx-2.3-22b-distilled-1.1.safetensors"
TE = "gemma_3_12B_it_fp4_mixed.safetensors"
LTX_FPS = 24

ROOT = "/root/reels_ltx29"
IMG_ROOT = "/root/reels_r3/img"
TTS_ROOT = "/root/reels_r3/tts"
BED = "/root/reels_r3/bed.wav"
INPUT = "/root/ComfyUI/input"
CLIPS_M = os.path.join(ROOT, "clips_m")
CLIPS_D = os.path.join(ROOT, "clips_d")
OUT_M = os.path.join(ROOT, "out_mobile")
OUT_D = os.path.join(ROOT, "out_desktop")
BUILD = os.path.join(ROOT, "build")
MAN = "/root/reels_r3/manifest_29aug_all.json"

for d in (CLIPS_M, CLIPS_D, OUT_M, OUT_D, BUILD):
    os.makedirs(d, exist_ok=True)

reels = json.load(open(MAN, encoding='utf-8'))['reels']
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else reels[0]['channel']
reels = [r for r in reels if r['channel'] == CHANNEL]

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def lang_of(v): return v.split('-')[0]
def esc(t): return t.replace('\\','\\\\').replace('{','\\{').replace('}','\\}')
def ts(s):
    h=int(s//3600); m=int((s%3600)//60); sec=s%60
    return f"{h}:{m:02d}:{sec:05.2f}"

FONTS = {'ar':'Noto Naskh Arabic','zh':'Noto Sans CJK SC','es':'Noto Sans','en':'Noto Sans'}
FPS = 30
LEAD = 0.4; GAP = 0.5; TAIL = 0.9; MINPANEL = 11.0; RECAP = 13.0

def ltx_prompt(s):
    p = s.replace('LTX motion:', 'Camera motion:')
    for tok in ('cinematic film still','vertical composition','horizontal composition'):
        p = p.replace(tok, '')
    while ',,' in p: p = p.replace(',,', ',')
    return p.strip(' ,')

NEG = ("blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, "
    "excessive noise, grainy texture, poor lighting, flickering, motion blur, distorted proportions, "
    "unnatural skin tones, deformed facial features, asymmetrical face, missing facial features, extra limbs, "
    "disfigured hands, wrong hand count, artifacts around text, unreadable text, inconsistent perspective, "
    "camera shake, incorrect depth of field, background too sharp, background clutter, jittery movement, "
    "awkward pauses, incorrect timing, unnatural transitions, inconsistent framing, tilted camera, "
    "flat lighting, inconsistent tone, stylized filters, or AI artifacts.")
SIGMAS = "1., 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"

def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(), {"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=60).read())

def frames_for(dsec):
    f = int(dsec * LTX_FPS) + 1
    return ((f - 1 + 7)//8)*8 + 1

_dur = {}
def get_dur(p):
    if p not in _dur:
        r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p], capture_output=True)
        _dur[p] = float(r.stdout.decode().strip())
    return _dur[p]

def flf_workflow(first, last, prompt, width, height, frames, seed, prefix):
    return {
        "1":{"class_type":"LoadImage","inputs":{"image":first}},
        "2":{"class_type":"LoadImage","inputs":{"image":last}},
        "3":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CKPT}},
        "4":{"class_type":"LTXAVTextEncoderLoader","inputs":{"text_encoder":TE,"ckpt_name":CKPT,"device":"default"}},
        "5":{"class_type":"LTXVAudioVAELoader","inputs":{"ckpt_name":CKPT}},
        "6":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["4",0]}},
        "7":{"class_type":"CLIPTextEncode","inputs":{"text":NEG,"clip":["4",0]}},
        "8":{"class_type":"PrimitiveInt","inputs":{"value":width}},
        "9":{"class_type":"PrimitiveInt","inputs":{"value":height}},
        "10":{"class_type":"PrimitiveInt","inputs":{"value":LTX_FPS}},
        "11":{"class_type":"ResizeImageMaskNode","inputs":{"input":["1",0],"resize_type":"scale dimensions","resize_type.width":["8",0],"resize_type.height":["9",0],"resize_type.crop":"center","scale_method":"nearest-exact"}},
        "12":{"class_type":"ResizeImageMaskNode","inputs":{"input":["2",0],"resize_type":"scale dimensions","resize_type.width":["8",0],"resize_type.height":["9",0],"resize_type.crop":"center","scale_method":"nearest-exact"}},
        "13":{"class_type":"GetImageSize","inputs":{"image":["12",0]}},
        "14":{"class_type":"LTXVPreprocess","inputs":{"image":["11",0],"img_compression":25}},
        "15":{"class_type":"LTXVPreprocess","inputs":{"image":["12",0],"img_compression":25}},
        "16":{"class_type":"EmptyLTXVLatentVideo","inputs":{"width":["13",0],"height":["13",1],"length":frames,"batch_size":1}},
        "17":{"class_type":"LTXVConditioning","inputs":{"positive":["6",0],"negative":["7",0],"frame_rate":["34",0]}},
        "18":{"class_type":"LTXVAddGuide","inputs":{"positive":["17",0],"negative":["17",1],"vae":["3",2],"latent":["16",0],"image":["14",0],"frame_idx":0,"strength":0.7}},
        "19":{"class_type":"LTXVAddGuide","inputs":{"positive":["18",0],"negative":["18",1],"vae":["3",2],"latent":["18",2],"image":["15",0],"frame_idx":-1,"strength":0.7}},
        "20":{"class_type":"LTXVEmptyLatentAudio","inputs":{"frames_number":frames,"frame_rate":["10",0],"batch_size":1,"audio_vae":["5",0]}},
        "21":{"class_type":"LTXVConcatAVLatent","inputs":{"video_latent":["19",2],"audio_latent":["20",0]}},
        "22":{"class_type":"CFGGuider","inputs":{"model":["3",0],"positive":["19",0],"negative":["19",1],"cfg":1.0}},
        "23":{"class_type":"SamplerEulerAncestral","inputs":{"eta":0.0,"s_noise":1.0}},
        "24":{"class_type":"ManualSigmas","inputs":{"sigmas":SIGMAS}},
        "25":{"class_type":"RandomNoise","inputs":{"noise_seed":seed}},
        "26":{"class_type":"SamplerCustomAdvanced","inputs":{"noise":["25",0],"guider":["22",0],"sampler":["23",0],"sigmas":["24",0],"latent_image":["21",0]}},
        "27":{"class_type":"LTXVSeparateAVLatent","inputs":{"av_latent":["26",0]}},
        "28":{"class_type":"LTXVCropGuides","inputs":{"positive":["19",0],"negative":["19",1],"latent":["27",0]}},
        "29":{"class_type":"VAEDecodeTiled","inputs":{"samples":["28",2],"vae":["3",2],"tile_size":768,"overlap":64,"temporal_size":64,"temporal_overlap":8}},
        "30":{"class_type":"LTXVAudioVAEDecode","inputs":{"samples":["27",1],"audio_vae":["5",0]}},
        "34":{"class_type":"ComfyMathExpression","inputs":{"expression":"a","values.a":["10",0]}},
        "31":{"class_type":"CreateVideo","inputs":{"images":["29",0],"fps":["34",0],"audio":["30",0]}},
        "32":{"class_type":"SaveVideo","inputs":{"video":["31",0],"filename_prefix":prefix,"format":"mp4","codec":"h264"}},
    }

def build_timeline(r):
    rid = r['id']
    ev = []; audio = []; panels = []; cur = 0.0
    for k in range(3):
        nk = get_dur(os.path.join(TTS_ROOT, f"{rid}_L{k+1}.mp3"))
        pstart = cur; s0 = cur + LEAD
        pend = max(pstart + MINPANEL, s0 + nk + TAIL)
        audio.append((os.path.join(TTS_ROOT, f"{rid}_L{k+1}.mp3"), int(round(s0*1000))))
        ev.append((s0-0.05, pend-0.1, 'Tgt', r['narration'][k]))
        panels.append((pstart, pend, k))
        cur = pend
    pstart = cur; wcur = cur + LEAD
    for j, w in enumerate(r['words']):
        fk = get_dur(os.path.join(TTS_ROOT, f"{rid}_w{j+1}.mp3")); tk = get_dur(os.path.join(TTS_ROOT, f"{rid}_t{j+1}.mp3"))
        s0 = wcur
        audio.append((os.path.join(TTS_ROOT, f"{rid}_w{j+1}.mp3"), int(round(s0*1000))))
        audio.append((os.path.join(TTS_ROOT, f"{rid}_t{j+1}.mp3"), int(round((s0+fk+0.15)*1000))))
        ev.append((s0-0.05, s0+fk+tk+0.8, 'Src', w['src']))
        ev.append((s0-0.05, s0+fk+tk+0.8, 'Tgt', w['tgt']))
        wcur = s0 + fk + tk + 0.6
    pend = max(pstart + RECAP, wcur + 0.5)
    panels.append((pstart, pend, 3))
    return panels, ev, audio, pend

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

def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError('CMD FAIL ' + cmd[0] + ' :: ' + p.stderr.decode()[-300:])

def build_clip_seg(clip, out, target_dur, frames, tw, th):
    vf = f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},setsar=1,fps=30"
    run(['ffmpeg','-y','-i',clip,'-t',f"{target_dur:.3f}",'-vf',vf,'-frames:v',str(frames),
         '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-an', out])

def build_static_recap(img, out, frames, tw, th):
    zoom = f"zoompan=z='1.09':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={tw}x{th}:fps=30"
    vf = f"scale={tw*2}:{th*2}:force_original_aspect_ratio=increase,crop={tw*2}:{th*2},{zoom}"
    run(['ffmpeg','-y','-loop','1','-i',img,'-vf',vf,'-frames:v',str(frames),
         '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p', out])

def assemble(r, clips_dir, out_dir, tw, th, clip_prefix):
    rid = r['id']
    d = os.path.join(BUILD, f"{rid}_{tw}x{th}")
    os.makedirs(d, exist_ok=True)
    panels, ev, audio, total = build_timeline(r)
    assp = os.path.join(d, rid + '.ass')
    open(assp, 'w', encoding='utf-8').write(make_ass(r, ev))
    segs = []
    for i,(pstart,pend,k) in enumerate(panels):
        frames = max(30, int(round((pend-pstart)*FPS)))
        seg = os.path.join(d, f"seg{k+1}.mp4")
        if k < 3:
            clip = os.path.join(clips_dir, f"{clip_prefix}_p{k+1}.mp4")
            if not os.path.exists(clip): raise RuntimeError(f"missing clip {clip}")
            build_clip_seg(clip, seg, pend-pstart, frames, tw, th)
        else:
            img = os.path.join(IMG_ROOT, f"{rid}_s{k+1}.png")
            build_static_recap(img, seg, frames, tw, th)
        segs.append(seg)
    lst = os.path.join(d, 'segs.txt')
    open(lst,'w').write("".join(f"file '{s}'\n" for s in segs))
    vsub = os.path.join(d, 'vsub.mp4')
    run(['ffmpeg','-y','-f','concat','-safe','0','-i',lst,
         '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p', vsub])
    out = os.path.join(out_dir, r['channel'], rid + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copy(assp, os.path.join(out_dir, r['channel'], rid + '.ass'))
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
    return out, total

def build_jobs():
    jobs = []
    for r in reels:
        rid = r['id']
        panels, ev, audio, total = build_timeline(r)
        for k in range(3):
            pstart, pend, _ = panels[k]
            frames = frames_for(pend - pstart)
            first = f"{rid}_s{k+1}.png"; last = f"{rid}_s{k+2}.png"
            for f in (first, last):
                src = os.path.join(IMG_ROOT, f); dst = os.path.join(INPUT, f)
                if not os.path.exists(dst): shutil.copy(src, dst)
            pm = ltx_prompt(r['scenes'][k])
            jobs.append({'rid':rid,'k':k,'aspect':'mobile','first':first,'last':last,'prompt':pm,'w':768,'h':1344,'frames':frames,'seed':r['seed']*10+k,'prefix':f"{rid}_m_p{k+1}"})
            jobs.append({'rid':rid,'k':k,'aspect':'desktop','first':first,'last':last,'prompt':pm,'w':1344,'h':768,'frames':frames,'seed':r['seed']*10+k+1000,'prefix':f"{rid}_d_p{k+1}"})
    return jobs

def main():
    t0 = time.time()
    jobs = build_jobs()
    log(f"CHANNEL={CHANNEL} REELS={len(reels)} CLIPS={len(jobs)}")
    active = []
    for j in jobs:
        wf = flf_workflow(j['first'], j['last'], j['prompt'], j['w'], j['h'], j['frames'], j['seed'], j['prefix'])
        try:
            pid = post(BASE + "/prompt", {"prompt": wf})["prompt_id"]
            active.append((j, pid))
        except Exception as e:
            log(f"SUBMIT_FAIL {j['prefix']}: {str(e)[:120]}")
    done_clips = {}; assembled = set()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    def do_assemble(rid):
        r = [x for x in reels if x['id'] == rid][0]
        try:
            m, mt = assemble(r, CLIPS_M, OUT_M, 1080, 1920, rid+"_m")
            dd, dt = assemble(r, CLIPS_D, OUT_D, 1920, 1080, rid+"_d")
            log(f"DONE {rid} mobile={mt:.1f}s desktop={dt:.1f}s")
        except Exception as e:
            log(f"ASSEMBLE_FAIL {rid}: {str(e)[:200]}")
    while len(done_clips) < len(active):
        for j, pid in active:
            key = j['prefix']
            if key in done_clips: continue
            try: st = get(BASE + "/history/" + pid)
            except Exception: continue
            rec = st.get(pid)
            if not rec: continue
            s = rec.get('status', {})
            if s.get('status_str') == 'error':
                log(f"ERROR {key}"); done_clips[key] = 'ERR'; continue
            if s.get('completed'):
                fn = None; sub = ''
                for nid, node in rec.get('outputs', {}).items():
                    for nm, val in node.items():
                        if nm in ('images','videos') and isinstance(val, list):
                            for v in val:
                                if isinstance(v, dict) and v.get('filename','').endswith('.mp4'):
                                    fn = v['filename']; sub = v.get('subfolder','')
                if fn:
                    clips = CLIPS_M if j['aspect'] == 'mobile' else CLIPS_D
                    url = BASE + "/view?" + urllib.parse.urlencode({"filename":fn,"subfolder":sub,"type":"output"})
                    open(os.path.join(clips, key + ".mp4"), 'wb').write(urllib.request.urlopen(url, timeout=180).read())
                    done_clips[key] = 'OK'
                    okc = sum(1 for x in done_clips.values() if x == 'OK')
                    log(f"CLIP {key} done={okc}/{len(active)} elapsed={int(time.time()-t0)}s")
                else:
                    done_clips[key] = 'ERR'; log(f"NOOUT {key}")
        for r in reels:
            rid = r['id']
            if rid in assembled: continue
            keys = [f"{rid}_m_p{k+1}" for k in range(3)] + [f"{rid}_d_p{k+1}" for k in range(3)]
            if all(done_clips.get(k) == 'OK' for k in keys):
                assembled.add(rid); pool.submit(do_assemble, rid)
        time.sleep(2)
    pool.shutdown(wait=True)
    errs = [k for k,v in done_clips.items() if v != 'OK']
    log(f"CHANNEL {CHANNEL} COMPLETE ok={len(active)-len(errs)}/{len(active)} errors={errs} total={int(time.time()-t0)}s")

if __name__ == "__main__":
    main()

