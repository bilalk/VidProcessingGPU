# flux_v2.py - FLUX for NEW schema (single scene: scenes[0].image_prompt)
import json, urllib.request, urllib.parse, time, os, sys, re

BASE = 'http://127.0.0.1:8188'
ROOT = '/root/reels_r3'
IMG = os.path.join(ROOT, 'img')
os.makedirs(IMG, exist_ok=True)
MAN = sys.argv[1] if len(sys.argv) > 1 else 'manifest_v2_100.json'
reels = json.load(open(os.path.join(ROOT, MAN), encoding='utf-8'))['reels']

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def still_prompt(s):
    # strip any "LTX motion:" / "motion:" suffix noise (new schema keeps motion separate anyway)
    i = s.find('LTX motion:')
    if i == -1: i = s.find('motion:')
    if i == -1: return s
    j = s.find('cinematic film still', i)
    head = s[:i].rstrip(', ')
    tail = s[j:] if j != -1 else ''
    return (head + ', ' + tail).strip(' ,') if head else s

def build(prompt, seed, prefix):
    return {
      "11": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux"}},
      "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "flux1-dev.safetensors"}},
      "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["11", 0]}},
      "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["11", 0]}},
      "3": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 16, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
      "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 1344, "batch_size": 1}},
      "8": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
      "9": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["8", 0]}},
      "10": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["9", 0]}},
    }

def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(), {'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=45).read())

def submit(prefix, prompt, seed):
    return post(BASE + '/prompt', {'prompt': build(still_prompt(prompt), seed, prefix)})['prompt_id']

def fetch_png(prefix, rec):
    fn = None; sub = ''
    for nid, outn in rec.get('outputs', {}).items():
        imgs = outn.get('images')
        if isinstance(imgs, list):
            for f in imgs:
                if f.get('filename', '').endswith('.png'):
                    fn = f['filename']; sub = f.get('subfolder', '')
    if not fn: raise RuntimeError('no_png')
    url = BASE + '/view?' + urllib.parse.urlencode({'filename': fn, 'subfolder': sub, 'type': 'output'})
    open(os.path.join(IMG, prefix + '.png'), 'wb').write(urllib.request.urlopen(url, timeout=120).read())

todo = []
for r in reels:
    prefix = f"{r['id']}_s1"
    out = os.path.join(IMG, prefix + '.png')
    if not (os.path.exists(out) and os.path.getsize(out) > 100000):
        todo.append((prefix, r['scenes'][0]['image_prompt'], r['seed']))

log(f"FLUX_V2 todo={len(todo)}")
active = []
for prefix, prompt, seed in todo:
    try:
        active.append((prefix, submit(prefix, prompt, seed)))
    except Exception as e:
        log(f"SUBMIT_FAIL {prefix}: {str(e)[:100]}")
log(f"FLUX_V2 submitted={len(active)}")

t0 = time.time()
done = {}
while len(done) < len(active):
    for prefix, pid in active:
        if prefix in done: continue
        try: st = get(BASE + '/history/' + pid)
        except Exception: continue
        rec = st.get(pid)
        if not rec: continue
        s = rec.get('status', {})
        if s.get('status_str') == 'error':
            log(f"{prefix} ERROR"); done[prefix] = 'ERR'; continue
        if s.get('completed'):
            try:
                fetch_png(prefix, rec)
                sz = os.path.getsize(os.path.join(IMG, prefix + '.png'))
                log(f"OK {prefix} ({sz//1024}KB) done={len(done)+1}/{len(active)}")
                done[prefix] = 'OK'
            except Exception as e:
                log(f"FETCH_FAIL {prefix}: {str(e)[:100]}"); done[prefix] = 'ERR'
    time.sleep(2)

errs = [p for p,v in done.items() if v == 'ERR']
if errs:
    log(f"FLUX_V2_ERRORS: {errs}"); sys.exit(1)
log(f"FLUX_V2_ALL_DONE total={int(time.time()-t0)}s images={len(todo)}")
