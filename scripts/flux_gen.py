import json, urllib.request, urllib.parse, time, os, sys

BASE = 'http://127.0.0.1:8188'
ROOT = '/root/reels'
IMG = os.path.join(ROOT, 'img')
os.makedirs(IMG, exist_ok=True)
reels = json.load(open(os.path.join(ROOT, 'manifest.json')))['reels']

def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

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
      "10": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["9", 0]}}
    }

def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(), {'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=60).read())

jobs = []
for r in reels:
    for k, scene in enumerate(r['scenes']):
        prefix = f"{r['id']}_s{k+1}"
        out = os.path.join(IMG, prefix + '.png')
        if os.path.exists(out) and os.path.getsize(out) > 100000:
            log(f"skip {prefix} (cached)")
            continue
        pid = post(BASE + '/prompt', {'prompt': build(scene, r['seed'] * 10 + k, prefix)})['prompt_id']
        jobs.append((prefix, pid))
        log(f"submitted {prefix} pid={pid}")

done = {}
t0 = time.time()
while len(done) < len(jobs):
    for prefix, pid in jobs:
        if prefix in done:
            continue
        try:
            st = get(BASE + '/history/' + pid)
        except Exception:
            continue
        if pid not in st:
            continue
        rec = st[pid]
        s = rec.get('status', {})
        if s.get('status_str') == 'error':
            log(f"{prefix} ERROR {json.dumps(s)[:300]}")
            done[prefix] = 'ERR'
            continue
        if s.get('completed'):
            fn = None; sub = ''
            for nid, outn in rec.get('outputs', {}).items():
                imgs = outn.get('images')
                if isinstance(imgs, list):
                    for f in imgs:
                        if f.get('filename', '').endswith('.png'):
                            fn = f['filename']; sub = f.get('subfolder', '')
            if fn:
                url = BASE + '/view?' + urllib.parse.urlencode({'filename': fn, 'subfolder': sub, 'type': 'output'})
                data = urllib.request.urlopen(url, timeout=300).read()
                open(os.path.join(IMG, prefix + '.png'), 'wb').write(data)
                log(f"{prefix} DONE ({len(data)//1024} KB) elapsed={int(time.time()-t0)}s")
            else:
                log(f"{prefix} completed but NO png")
            done[prefix] = 'OK'
    time.sleep(4)

err = [p for p, v in done.items() if v == 'ERR']
if err:
    log(f"FLUX_ERRORS: {err}")
    sys.exit(1)
log(f"FLUX_ALL_DONE total={int(time.time()-t0)}s jobs={len(jobs)}")
