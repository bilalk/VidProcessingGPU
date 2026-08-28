#!/usr/bin/env python
# run_ltx_full.py - full LTX-2.3 B07 production orchestrator.
# Burst-generates 48 FLF clips, assembles 12 reels (mobile 9:16 + desktop 16:9),
# and emits per-reel DONE markers for incremental pull.
import json, os, sys, time, subprocess, threading, shutil, urllib.request, urllib.parse, concurrent.futures

BASE = "http://127.0.0.1:8188"
CKPT = "ltx-2.3-22b-distilled-fp8.safetensors"
TE = "gemma_3_12B_it_fp4_mixed.safetensors"

ROOT = "/root/reels_ltx"
IMG_ROOT = "/root/reels_r3/img"
TTS_ROOT = "/root/reels_r3/tts"
BED = "/root/reels_r3/bed.wav"
INPUT = "/root/ComfyUI/input"
CLIPS = os.path.join(ROOT, "clips")
OUT_M = os.path.join(ROOT, "out_mobile")
OUT_D = os.path.join(ROOT, "out_desktop")
BUILD = os.path.join(ROOT, "build")
LOGS = os.path.join(ROOT, "logs")
DONE = os.path.join(ROOT, "done")
MAN = "/root/reels_r3/manifest_r4_b07_renumbered.json"

FPS = 30
LEAD = 0.35
GAP = 0.30
TAIL = 0.55
MINPANEL = 7.5
RECAP = 3.4
LTX_FPS = 24

FONTS = {'en': 'Noto Sans', 'es': 'Noto Sans', 'zh': 'Noto Sans CJK SC', 'ar': 'Noto Naskh Arabic'}
MOTION = "Smooth cinematic camera movement and natural subject motion as the scene progresses, keeping the character, lighting, and composition consistent."

for d in (CLIPS, OUT_M, OUT_D, BUILD, LOGS, DONE):
    os.makedirs(d, exist_ok=True)

reels = json.load(open(MAN, encoding='utf-8'))['reels']

def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def lang_of(v): return v.split('-')[0]
def esc(t): return t.replace('\\','\\\\').replace('{','\\{').replace('}','\\}')
def ts(s):
    h=int(s//3600); m=int((s%3600)//60); sec=s%60
    return f"{h}:{m:02d}:{sec:05.2f}"

_durc = {}
def get_dur(p):
    if p not in _durc:
        r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p], capture_output=True)
        _durc[p] = float(r.stdout.decode().strip())
    return _durc[p]

def tp(rid, name): return os.path.join(TTS_ROOT, f"{rid}_{name}.mp3")

# ---------- timeline (identical to assemble5) ----------
def build_timeline(r):
    rid = r['id']
    ls = lang_of(r['voice_src']); lt = lang_of(r['voice_tgt'])
    ev=[]; audio=[]; panels=[]; cur=0.0
    for k, line in enumerate(r['lines']):
        pstart=cur
        da=get_dur(tp(rid,f"L{k+1}a")); db=get_dur(tp(rid,f"L{k+1}b"))
        s0=cur+LEAD; t0=s0+da+GAP
        audio.append((tp(rid,f"L{k+1}a"), int(round(s0*1000))))
        audio.append((tp(rid,f"L{k+1}b"), int(round(t0*1000))))
        pend=max(pstart+MINPANEL, t0+db+TAIL)
        ev.append((s0-0.05, min(s0+da+0.25, pend-0.1), 'Src', line['src']))
        ev.append((t0-0.05, pend-0.15, 'Tgt', line['tgt']))
        if line.get('translit'):
            ev.append((t0-0.05, pend-0.15, 'Tr', line['translit']))
        panels.append((pstart, pend, k))
        cur=pend
    pstart=cur; wcur=cur+LEAD
    for j,w in enumerate(r['words']):
        da=get_dur(tp(rid,f"w{j+1}a")); db=get_dur(tp(rid,f"w{j+1}b"))
        s0=wcur; t0=s0+da+GAP; wend=t0+db
        audio.append((tp(rid,f"w{j+1}a"), int(round(s0*1000))))
        audio.append((tp(rid,f"w{j+1}b"), int(round(t0*1000))))
        wt = w['src'].title() if ls=='en' else w['src']
        wb = w['tgt'].title() if lt=='en' else w['tgt']
        if w.get('translit'): wb = wb + "  (" + w['translit'] + ")"
        ev.append((s0-0.05, wend+0.30, 'Src', wt))
        ev.append((s0-0.05, wend+0.30, 'Tgt', wb))
        wcur=wend+0.45
    rstart=wcur+0.35; rend=rstart+RECAP
    ys={1:[960],2:[860,1120],3:[700,960,1220]}[len(r['words'])]
    for j,w in enumerate(r['words']):
        wt = w['src'].title() if ls=='en' else w['src']
        wb = w['tgt'].title() if lt=='en' else w['tgt']
        if w.get('translit'): wb = wb + "  (" + w['translit'] + ")"
        ev.append((rstart, rend, 'Src', '{\\pos(540,%d)}'%ys[j] + wt))
        ev.append((rstart, rend, 'Tgt', '{\\pos(540,%d)}'%(ys[j]+64) + wb))
    pend=max(pstart+MINPANEL, wcur+0.25, rend+0.35)
    panels.append((pstart, pend, 3))
    cur=pend
    return panels, ev, audio, cur

def make_ass(r, ev):
    ls=lang_of(r['voice_src']); lt=lang_of(r['voice_tgt'])
    fs=FONTS.get(ls,'Noto Sans'); ft=FONTS.get(lt,'Noto Sans')
    head=(
        "[Script Info]\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Src,{fs},56,&H00FFFFFF,&H00FFFFFF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,8,70,70,170,1\n"
        f"Style: Tgt,{ft},62,&H0000D7FF,&H0000D7FF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,2,70,70,330,1\n"
        f"Style: Tr,{ft},38,&H00E8E8E8,&H00E8E8E8,&H90000000,&H90000000,0,2,0,0,100,100,0,0,1,2.5,1,2,70,70,210,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines=[]
    for (a,b,st,txt) in ev:
        body = txt if txt.startswith('{\\pos(') else esc(txt)
        lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},{st},,0,0,0,,{body}")
    return head + "\n".join(lines) + "\n"

def run_cmd(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError('CMD FAIL ' + cmd[0] + ' :: ' + p.stderr.decode()[-400:])

ZOOM_RECAP = "zoompan=z='1.09':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/{n}':d={n}:s=1080x1920:fps=30"

def build_static_recap(img, out, frames):
    vf = f"scale=1536:2688:force_original_aspect_ratio=increase,crop=1536:2688,{ZOOM_RECAP.format(n=frames)}"
    run_cmd(['ffmpeg','-y','-loop','1','-i',img,'-vf',vf,'-frames:v',str(frames),
             '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p', out])

def build_clip_seg(clip, out, target_dur, frames):
    # trim to target duration, scale to 1080x1920, force 30fps
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"
    run_cmd(['ffmpeg','-y','-i',clip,'-t',f"{target_dur:.3f}",'-vf',vf,
             '-frames:v',str(frames),'-c:v','libx264','-preset','veryfast','-crf','19',
             '-pix_fmt','yuv420p','-an', out])

def assemble_mobile(r):
    rid = r['id']
    d = os.path.join(BUILD, rid)
    os.makedirs(d, exist_ok=True)
    panels, ev, audio, total = build_timeline(r)
    assp = os.path.join(d, rid + '.ass')
    open(assp,'w',encoding='utf-8').write(make_ass(r, ev))

    segs=[]
    for i,(pstart,pend,k) in enumerate(panels):
        frames = max(30, int(round((pend-pstart)*FPS)))
        seg = os.path.join(d, f"seg{k+1}.mp4")
        if k < 3:
            clip = os.path.join(CLIPS, f"{rid}_p{k+1}.mp4")
            if not (os.path.exists(seg) and os.path.getsize(seg) > 100000):
                build_clip_seg(clip, seg, pend-pstart, frames)
        else:
            img = os.path.join(IMG_ROOT, f"{rid}_s{k+1}.png")
            if not (os.path.exists(seg) and os.path.getsize(seg) > 100000):
                build_static_recap(img, seg, frames)
        segs.append(seg)

    lst = os.path.join(d,'segs.txt')
    open(lst,'w').write("".join(f"file '{s}'\n" for s in segs))

    vsub = os.path.join(d,'vsub.mp4')
    run_cmd(['ffmpeg','-y','-f','concat','-safe','0','-i',lst,
             '-vf',f"ass={assp}",'-c:v','libx264','-preset','veryfast',
             '-crf','19','-pix_fmt','yuv420p', vsub])

    out = os.path.join(OUT_M, r['channel'], rid + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n=len(audio)
    fc="".join(f"[{i+1}]adelay={ms}|{ms}[a{i}];" for i,(p,ms) in enumerate(audio))
    fc+=f"[{n+1}]volume=0.13[mus];"
    fc+="".join(f"[a{i}]" for i in range(n))
    fc+="[mus]amix=inputs=%d:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]"%(n+1)
    cmd=['ffmpeg','-y','-i',vsub]
    for (p,ms) in audio: cmd+=['-i',p]
    cmd+=['-stream_loop','-1','-i',BED,'-filter_complex',fc,'-map','0:v','-map','[a]',
          '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
          '-c:a','aac','-b:a','160k','-t',f"{total:.2f}",'-movflags','+faststart',out]
    run_cmd(cmd)

    # script + ass copies
    sp = os.path.join(OUT_M, r['channel'], rid + '.script.txt')
    with open(sp,'w',encoding='utf-8') as f:
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
        for i,s in enumerate(r['scenes']):
            f.write(f"Scene {i+1}: {s}\n")
    shutil.copy(assp, os.path.join(OUT_M, r['channel'], rid + '.ass'))
    return out, total

def assemble_desktop(r, mobile_mp4):
    rid = r['id']
    out = os.path.join(OUT_D, r['channel'], rid + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # blurred-fill pillarbox: 9:16 centered in 16:9 1920x1080
    fc = ("[0:v]split=2[bg][fg];"
          "[bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=20:2[bg];"
          "[fg]scale=-2:1080[fg];"
          "[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1[v]")
    run_cmd(['ffmpeg','-y','-i',mobile_mp4,'-filter_complex',fc,'-map','[v]','-map','0:a',
             '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
             '-c:a','copy','-movflags','+faststart', out])
    return out

# ---------- LTX workflow ----------
def ltx_workflow(first, last, frames, seed, prefix):
    negative = ("blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, "
        "excessive noise, grainy texture, poor lighting, flickering, motion blur, distorted proportions, "
        "unnatural skin tones, deformed facial features, asymmetrical face, missing facial features, "
        "extra limbs, disfigured hands, wrong hand count, artifacts around text, unreadable text, "
        "inconsistent perspective, camera shake, incorrect depth of field, background too sharp, "
        "background clutter, distracting reflections, harsh shadows, inconsistent lighting direction, "
        "color banding, cartoonish rendering, 3D CGI look, unrealistic materials, uncanny valley effect, "
        "incorrect ethnicity, wrong gender, exaggerated expressions, smiling, laughing, exaggerated sadness, "
        "wrong gaze direction, eyes looking at camera, mismatched lip sync, silent or muted audio, distorted voice, "
        "robotic voice, echo, background noise, off-sync audio, incorrect dialogue, added dialogue, repetitive speech, "
        "jittery movement, awkward pauses, incorrect timing, unnatural transitions, inconsistent framing, tilted camera, "
        "missing shallow depth of field, flat lighting, inconsistent tone, cinematic oversaturation, stylized filters, or AI artifacts.")
    sigmas = "1., 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"
    wf = {
        "1":{"class_type":"LoadImage","inputs":{"image":first}},
        "2":{"class_type":"LoadImage","inputs":{"image":last}},
        "3":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CKPT}},
        "4":{"class_type":"LTXAVTextEncoderLoader","inputs":{"text_encoder":TE,"ckpt_name":CKPT,"device":"default"}},
        "5":{"class_type":"LTXVAudioVAELoader","inputs":{"ckpt_name":CKPT}},
        "6":{"class_type":"CLIPTextEncode","inputs":{"text":MOTION,"clip":["4",0]}},
        "7":{"class_type":"CLIPTextEncode","inputs":{"text":negative,"clip":["4",0]}},
        "8":{"class_type":"PrimitiveInt","inputs":{"value":768}},
        "9":{"class_type":"PrimitiveInt","inputs":{"value":1344}},
        "10":{"class_type":"PrimitiveInt","inputs":{"value":LTX_FPS}},
        "11":{"class_type":"ResizeImageMaskNode","inputs":{
            "input":["1",0],"resize_type":"scale dimensions",
            "resize_type.width":["8",0],"resize_type.height":["9",0],
            "resize_type.crop":"center","scale_method":"nearest-exact"}},
        "12":{"class_type":"ResizeImageMaskNode","inputs":{
            "input":["2",0],"resize_type":"scale dimensions",
            "resize_type.width":["8",0],"resize_type.height":["9",0],
            "resize_type.crop":"center","scale_method":"nearest-exact"}},
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
        "24":{"class_type":"ManualSigmas","inputs":{"sigmas":sigmas}},
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
    return wf

def post(url,data):
    req=urllib.request.Request(url,json.dumps(data).encode(),{"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
def get(url):
    return json.loads(urllib.request.urlopen(url,timeout=60).read())

def frames_for(dsec):
    frames = dsec*LTX_FPS + 1
    frames = ((int(frames) - 1 + 7)//8)*8 + 1
    return frames

def build_jobs():
    jobs=[]
    for r in reels:
        rid=r['id']
        panels, ev, audio, total = build_timeline(r)
        for k in range(3):
            pstart, pend, _ = panels[k]
            dsec = pend - pstart
            frames = frames_for(dsec)
            first = f"{rid}_s{k+1}.png"
            last = f"{rid}_s{k+2}.png"
            prefix = f"{rid}_p{k+1}"
            seed = r['seed']*10 + k
            # stage images
            for f in (first, last):
                src = os.path.join(IMG_ROOT, f)
                dst = os.path.join(INPUT, f)
                if not os.path.exists(dst):
                    shutil.copy(src, dst)
            jobs.append({'rid':rid,'k':k,'first':first,'last':last,'frames':frames,'seed':seed,'prefix':prefix})
    return jobs

def fetch_output(rec):
    for nid,node in rec.get('outputs',{}).items():
        for name,val in node.items():
            if name in ('images','videos') and isinstance(val,list):
                for v in val:
                    if isinstance(v,dict) and v.get('filename','').endswith('.mp4'):
                        return v
    return None

def main():
    t0 = time.time()
    jobs = build_jobs()
    log(f"TOTAL CLIPS={len(jobs)}")

    # burst submit
    active=[]
    for j in jobs:
        wf = ltx_workflow(j['first'], j['last'], j['frames'], j['seed'], j['prefix'])
        try:
            pid = post(BASE+"/prompt",{"prompt":wf})["prompt_id"]
            active.append((j, pid))
        except Exception as e:
            log(f"SUBMIT_FAIL {j['prefix']}: {e}")
    log(f"SUBMITTED {len(active)}/{len(jobs)}")

    done_clips = {}
    assembled = set()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    while len(done_clips) < len(active):
        for j,pid in active:
            key = j['prefix']
            if key in done_clips:
                continue
            try:
                st = get(BASE+"/history/"+pid)
            except Exception:
                continue
            rec = st.get(pid)
            if not rec:
                continue
            status = rec.get('status',{})
            if status.get('status_str') == 'error':
                log(f"ERROR {key}")
                done_clips[key] = 'ERR'
                continue
            if status.get('completed'):
                v = fetch_output(rec)
                if v:
                    dest = os.path.join(CLIPS, key+".mp4")
                    if not os.path.exists(dest) or os.path.getsize(dest) < 100000:
                        url = BASE+"/view?"+urllib.parse.urlencode({"filename":v["filename"],"subfolder":v.get("subfolder",""),"type":"output"})
                        data = urllib.request.urlopen(url, timeout=120).read()
                        open(dest,'wb').write(data)
                    done_clips[key] = 'OK'
                    log(f"CLIP {key} done={len([x for x in done_clips.values() if x=='OK'])}/{len(active)} elapsed={int(time.time()-t0)}s")
                else:
                    done_clips[key] = 'ERR'
                    log(f"NOOUT {key}")

        # assemble any reel whose 3 clips are done
        for r in reels:
            rid = r['id']
            if rid in assembled:
                continue
            keys = [f"{rid}_p{k+1}" for k in range(3)]
            if all(done_clips.get(k) == 'OK' for k in keys):
                assembled.add(rid)
                log(f"ASSEMBLE {rid}")
                def do_assemble(rr=r):
                    try:
                        mobile, total = assemble_mobile(rr)
                        assemble_desktop(rr, mobile)
                        open(os.path.join(DONE, rr['id']+".done"),'w').write(f"done {time.time()}\n")
                        log(f"DONE {rr['id']} total={total:.1f}s")
                    except Exception as e:
                        log(f"ASSEMBLE_FAIL {rr['id']}: {e}")
                pool.submit(do_assemble)

        time.sleep(2)

    pool.shutdown(wait=True)
    errs = [k for k,v in done_clips.items() if v != 'OK']
    log(f"FULL RUN COMPLETE clips_ok={len(active)-len(errs)}/{len(active)} errors={errs} total={int(time.time()-t0)}s")

if __name__ == "__main__":
    main()
