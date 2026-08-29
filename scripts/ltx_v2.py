# ltx_v2.py - LTX-2.3 IMAGE-TO-VIDEO for the NEW single-scene schema (does NOT touch run_ltx_v3.py)
import json, os, sys, time, subprocess, shutil, urllib.request, urllib.parse, concurrent.futures

BASE = "http://127.0.0.1:8188"
CKPT = "ltx-2.3-22b-distilled-fp8.safetensors"
TE = "gemma_3_12B_it_fp4_mixed.safetensors"
LTX_FPS = 24

ROOT = "/root/reels_ltx2"
IMG_ROOT = "/root/reels_r3/img"
TTS_ROOT = "/root/reels_r3/tts"
BED = "/root/reels_r3/bed.wav"
INPUT = "/root/ComfyUI/input"
CLIPS = os.path.join(ROOT, "clips")
OUT_M = os.path.join(ROOT, "out_mobile")
OUT_D = os.path.join(ROOT, "out_desktop")
BUILD = os.path.join(ROOT, "build")
MAN = "/root/reels_r3/manifest_v2_100.json"

for d in (CLIPS, OUT_M, OUT_D, BUILD):
    os.makedirs(d, exist_ok=True)

reels = json.load(open(MAN, encoding='utf-8'))['reels']

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def lang_of(v): return v.split('-')[0]
def esc(t): return t.replace('\\','\\\\').replace('{','\\{').replace('}','\\}')
def ts(s):
    h=int(s//3600); m=int((s%3600)//60); sec=s%60
    return f"{h}:{m:02d}:{sec:05.2f}"

FONTS = {'ar':'Noto Naskh Arabic','zh':'Noto Sans CJK SC','es':'Noto Sans','en':'Noto Sans'}

NEG = ("blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, "
    "excessive noise, grainy texture, poor lighting, flickering, motion blur, distorted proportions, "
    "unnatural skin tones, deformed facial features, asymmetrical face, missing facial features, extra limbs, "
    "disfigured hands, wrong hand count, artifacts around text, unreadable text, inconsistent perspective, "
    "camera shake, incorrect depth of field, background too sharp, background clutter, jittery movement, "
    "awkward pauses, incorrect timing, unnatural transitions, inconsistent framing, tilted camera, "
    "flat lighting, inconsistent tone, stylized filters, or AI artifacts.")
SIGMAS = "1., 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"

def i2v_workflow(image, prompt, width, height, frames, seed, prefix):
    return {
        "1": {"class_type":"LoadImage","inputs":{"image":image}},
        "3": {"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CKPT}},
        "4": {"class_type":"LTXAVTextEncoderLoader","inputs":{"text_encoder":TE,"ckpt_name":CKPT,"device":"default"}},
        "5": {"class_type":"LTXVAudioVAELoader","inputs":{"ckpt_name":CKPT}},
        "6": {"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["4",0]}},
        "7": {"class_type":"CLIPTextEncode","inputs":{"text":NEG,"clip":["4",0]}},
        "8": {"class_type":"PrimitiveInt","inputs":{"value":width}},
        "9": {"class_type":"PrimitiveInt","inputs":{"value":height}},
        "10": {"class_type":"PrimitiveInt","inputs":{"value":LTX_FPS}},
        "11": {"class_type":"ResizeImageMaskNode","inputs":{"input":["1",0],"resize_type":"scale dimensions","resize_type.width":["8",0],"resize_type.height":["9",0],"resize_type.crop":"center","scale_method":"nearest-exact"}},
        "13": {"class_type":"GetImageSize","inputs":{"image":["11",0]}},
        "14": {"class_type":"LTXVPreprocess","inputs":{"image":["11",0],"img_compression":25}},
        "16": {"class_type":"EmptyLTXVLatentVideo","inputs":{"width":["13",0],"height":["13",1],"length":frames,"batch_size":1}},
        "17": {"class_type":"LTXVConditioning","inputs":{"positive":["6",0],"negative":["7",0],"frame_rate":["34",0]}},
        "18": {"class_type":"LTXVAddGuide","inputs":{"positive":["17",0],"negative":["17",1],"vae":["3",2],"latent":["16",0],"image":["14",0],"frame_idx":0,"strength":0.7}},
        "20": {"class_type":"LTXVEmptyLatentAudio","inputs":{"frames_number":frames,"frame_rate":["10",0],"batch_size":1,"audio_vae":["5",0]}},
        "21": {"class_type":"LTXVConcatAVLatent","inputs":{"video_latent":["18",2],"audio_latent":["20",0]}},
        "22": {"class_type":"CFGGuider","inputs":{"model":["3",0],"positive":["18",0],"negative":["18",1],"cfg":1.0}},
        "23": {"class_type":"SamplerEulerAncestral","inputs":{"eta":0.0,"s_noise":1.0}},
        "24": {"class_type":"ManualSigmas","inputs":{"sigmas":SIGMAS}},
        "25": {"class_type":"RandomNoise","inputs":{"noise_seed":seed}},
        "26": {"class_type":"SamplerCustomAdvanced","inputs":{"noise":["25",0],"guider":["22",0],"sampler":["23",0],"sigmas":["24",0],"latent_image":["21",0]}},
        "27": {"class_type":"LTXVSeparateAVLatent","inputs":{"av_latent":["26",0]}},
        "28": {"class_type":"LTXVCropGuides","inputs":{"positive":["18",0],"negative":["18",1],"latent":["27",0]}},
        "29": {"class_type":"VAEDecodeTiled","inputs":{"samples":["28",2],"vae":["3",2],"tile_size":768,"overlap":64,"temporal_size":64,"temporal_overlap":8}},
        "30": {"class_type":"LTXVAudioVAEDecode","inputs":{"samples":["27",1],"audio_vae":["5",0]}},
        "34": {"class_type":"ComfyMathExpression","inputs":{"expression":"a","values.a":["10",0]}},
        "31": {"class_type":"CreateVideo","inputs":{"images":["29",0],"fps":["34",0],"audio":["30",0]}},
        "32": {"class_type":"SaveVideo","inputs":{"video":["31",0],"filename_prefix":prefix,"format":"mp4","codec":"h264"}},
    }

def post(url,data):
    req=urllib.request.Request(url,json.dumps(data).encode(),{"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
def get(url):
    return json.loads(urllib.request.urlopen(url,timeout=60).read())

def frames_for(dsec):
    f = int(dsec * LTX_FPS) + 1
    return ((f - 1 + 7)//8)*8 + 1

def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError('CMD FAIL ' + cmd[0] + ' :: ' + p.stderr.decode()[-350:])

RECAP = 2.0

def make_ass(r, dur):
    fs = FONTS.get(lang_of(r['voice_src']), 'Noto Sans')
    ft = FONTS.get(lang_of(r['voice_tgt']), 'Noto Sans')
    head = ("[Script Info]\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Src,{fs},56,&H00FFFFFF,&H00FFFFFF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,8,70,70,170,1\n"
            f"Style: Tgt,{ft},62,&H0000D7FF,&H0000D7FF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,2,70,70,330,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ev = []
    for ln in r['lines']:
        st = 'Src' if ln['speaker'].startswith('voice_src') else 'Tgt'
        ev.append(f"Dialogue: 0,{ts(ln['start'])},{ts(ln['end'])},{st},,0,0,0,,{esc(ln['text'])}")
    ws = r['words']; rs = dur - RECAP
    ev.append(f"Dialogue: 0,{ts(rs)},{ts(dur)},Src,,0,0,0,,{esc(ws[0]+'   '+ws[1])}")
    ev.append(f"Dialogue: 0,{ts(rs)},{ts(dur)},Tgt,,0,0,0,,{esc(ws[2]+'   '+ws[3])}")
    return head + "\n".join(ev) + "\n"

def assemble(r, clip, out_dir, tw, th, dur):
    rid = r['id']
    d = os.path.join(BUILD, f"{rid}_{tw}x{th}")
    os.makedirs(d, exist_ok=True)
    assp = os.path.join(d, rid + '.ass')
    open(assp, 'w', encoding='utf-8').write(make_ass(r, dur))
    vsub = os.path.join(d, 'vsub.mp4')
    run(['ffmpeg','-y','-i',clip,'-t',f"{dur:.3f}",'-vf',
         f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},setsar=1,fps=30",
         '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-an', vsub])
    vsub2 = os.path.join(d, 'vsub2.mp4')
    run(['ffmpeg','-y','-i',vsub,'-vf',f'ass={assp}','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p', vsub2])
    out = os.path.join(out_dir, r['channel'], rid + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    L1 = os.path.join(TTS_ROOT, f"{rid}_L1.mp3"); L2 = os.path.join(TTS_ROOT, f"{rid}_L2.mp3")
    d1 = int(round(r['lines'][0]['start']*1000)); d2 = int(round(r['lines'][1]['start']*1000))
    fc = (f"[1]adelay={d1}|{d1}[a1];[2]adelay={d2}|{d2}[a2];[3]volume=0.13[mus];"
          "[a1][a2][mus]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    run(['ffmpeg','-y','-i',vsub2,'-i',L1,'-i',L2,'-stream_loop','-1','-i',BED,
         '-filter_complex',fc,'-map','0:v','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','19',
         '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-t',f"{dur:.2f}",'-movflags','+faststart', out])
    return out

def main():
    t0 = time.time()
    jobs = []
    for r in reels:
        rid = r['id']
        sc = r['scenes'][0]
        dur = sc['end_time'] + RECAP
        prompt = sc['image_prompt'] + ', ' + sc['motion']
        img = f"{rid}_s1.png"
        src = os.path.join(IMG_ROOT, img); dst = os.path.join(INPUT, img)
        if not os.path.exists(dst): shutil.copy(src, dst)
        jobs.append({'rid':rid,'img':img,'prompt':prompt,'w':768,'h':1344,'frames':frames_for(dur),'seed':r['seed'],'prefix':f"{rid}_ltx_m"})
        jobs.append({'rid':rid,'img':img,'prompt':prompt,'w':1344,'h':768,'frames':frames_for(dur),'seed':r['seed']+1000,'prefix':f"{rid}_ltx_d"})
    log(f"LTX_V2 TOTAL JOBS={len(jobs)} (mobile+desktop x {len(reels)} reels)")

    active = []
    for j in jobs:
        wf = i2v_workflow(j['img'], j['prompt'], j['w'], j['h'], j['frames'], j['seed'], j['prefix'])
        try:
            pid = post(BASE + "/prompt", {"prompt": wf})["prompt_id"]
            active.append((j, pid))
        except Exception as e:
            log(f"SUBMIT_FAIL {j['prefix']}: {str(e)[:120]}")

    done_clips = {}; assembled = set()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    def do_assemble(rid):
        r = [x for x in reels if x['id'] == rid][0]
        sc = r['scenes'][0]; dur = sc['end_time'] + RECAP
        try:
            assemble(r, os.path.join(CLIPS, f"{rid}_ltx_m.mp4"), OUT_M, 1080, 1920, dur)
            assemble(r, os.path.join(CLIPS, f"{rid}_ltx_d.mp4"), OUT_D, 1920, 1080, dur)
            log(f"DONE {rid} mobile+desktop dur={dur:.1f}s")
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
                        if nm in ('images', 'videos') and isinstance(val, list):
                            for v in val:
                                if isinstance(v, dict) and v.get('filename', '').endswith('.mp4'):
                                    fn = v['filename']; sub = v.get('subfolder', '')
                if fn:
                    url = BASE + "/view?" + urllib.parse.urlencode({"filename": fn, "subfolder": sub, "type": "output"})
                    open(os.path.join(CLIPS, key + ".mp4"), 'wb').write(urllib.request.urlopen(url, timeout=180).read())
                    done_clips[key] = 'OK'
                    okc = sum(1 for x in done_clips.values() if x == 'OK')
                    log(f"CLIP {key} done={okc}/{len(active)} elapsed={int(time.time()-t0)}s")
                else:
                    done_clips[key] = 'ERR'; log(f"NOOUT {key}")
        for r in reels:
            rid = r['id']
            if rid in assembled: continue
            if done_clips.get(f"{rid}_ltx_m") == 'OK' and done_clips.get(f"{rid}_ltx_d") == 'OK':
                assembled.add(rid); pool.submit(do_assemble, rid)
        time.sleep(2)
    pool.shutdown(wait=True)
    errs = [k for k, v in done_clips.items() if v != 'OK']
    log(f"LTX_V2 COMPLETE ok={len(active)-len(errs)}/{len(active)} errors={errs} total={int(time.time()-t0)}s")

if __name__ == "__main__":
    main()

