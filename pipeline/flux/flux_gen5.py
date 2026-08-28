# flux_gen5.py — R3 workspace version of flux_gen4.py (points to /root/reels_r3/).
# Sequential single-flight FLUX generator. One job at a time, verbose log.
import json, urllib.request, urllib.parse, time, os, sys

BASE = 'http://127.0.0.1:8188'
ROOT = '/root/reels_r3'
IMG = os.path.join(ROOT, 'img')
os.makedirs(IMG, exist_ok=True)
MAN = sys.argv[1] if len(sys.argv) > 1 else 'manifest_r3.json'
with open(os.path.join(ROOT, MAN), encoding='utf-8') as fh:
    reels = json.load(fh)['reels']
JOB_TIMEOUT = 240

def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def still_prompt(s):
    # FLUX still: strip the "LTX motion: ..." directive (between it and "cinematic film still")
    # so the image model gets a clean still, not motion instructions it cannot render.
    i = s.find('LTX motion:')
    if i == -1:
        return s
    j = s.find('cinematic film still', i)
    if j == -1:
        return s
    head = s[:i].rstrip(', ')
    return (head + ', ' + s[j:]) if head else s[j:]

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
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=45).read())

def submit(prefix, scene, seed):
    return post(BASE + '/prompt', {'prompt': build(still_prompt(scene), seed, prefix)})['prompt_id']

def fetch_png(prefix, rec):
    fn = None; sub = ''
    for nid, outn in rec.get('outputs', {}).items():
        imgs = outn.get('images')
        if isinstance(imgs, list):
            for f in imgs:
                if f.get('filename', '').endswith('.png'):
                    fn = f['filename']; sub = f.get('subfolder', '')
    if not fn:
        raise RuntimeError('no_png')
    url = BASE + '/view?' + urllib.parse.urlencode({'filename': fn, 'subfolder': sub, 'type': 'output'})
    data = urllib.request.urlopen(url, timeout=120).read()
    open(os.path.join(IMG, prefix + '.png'), 'wb').write(data)

def wait_job(prefix, pid, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            st = get(BASE + '/history/' + pid)
        except Exception:
            time.sleep(3); continue
        rec = st.get(pid)
        if rec:
            s = rec.get('status', {})
            if s.get('status_str') == 'error':
                raise RuntimeError('job_error: ' + str(rec)[:200])
            if s.get('completed'):
                fetch_png(prefix, rec)
                return
        time.sleep(2)
    raise RuntimeError('timeout')

todo = []
for r in reels:
    for k, scene in enumerate(r['scenes']):
        prefix = f"{r['id']}_s{k+1}"
        p = os.path.join(IMG, prefix + '.png')
        if not (os.path.exists(p) and os.path.getsize(p) > 100000):
            todo.append((prefix, scene, r['seed'] * 10 + k))

log(f"FLUX5 sequential todo={len(todo)}")
t0 = time.time()
fails = []
for i, (prefix, scene, seed) in enumerate(todo):
    ok = False
    for attempt in (1, 2, 3):
        try:
            pid = submit(prefix, scene, seed)
            wait_job(prefix, pid, JOB_TIMEOUT)
            sz = os.path.getsize(os.path.join(IMG, prefix + '.png'))
            log(f"{i+1}/{len(todo)} {prefix} OK ({sz//1024}KB) elapsed={int(time.time()-t0)}s")
            ok = True
            break
        except Exception as e:
            log(f"{i+1}/{len(todo)} {prefix} attempt{attempt} fail: {str(e)[:140]}")
            time.sleep(5)
    if not ok:
        fails.append(prefix)

if fails:
    log(f"FLUX5_ERRORS {fails}")
    sys.exit(1)
log(f"FLUX5_ALL_DONE total={int(time.time()-t0)}s images={len(todo)}")
