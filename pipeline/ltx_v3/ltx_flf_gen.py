#!/usr/bin/env python
# ltx_flf_gen.py - LTX-2.3 First/Last Frame clip generator (flat API graph)
# Correctly resolved from the built-in LTX-2.3 FLF template wiring.
import json, os, sys, time, urllib.request, urllib.parse

BASE = "http://127.0.0.1:8188"
CKPT = "ltx-2.3-22b-distilled-fp8.safetensors"
TE = "gemma_3_12B_it_fp4_mixed.safetensors"

def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def build_workflow(first_img, last_img, text, width, height, duration, fps, seed, prefix):
    frames = duration * fps + 1
    frames = ((frames - 1 + 7) // 8) * 8 + 1

    negative = (
        "blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, "
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
        "missing shallow depth of field, flat lighting, inconsistent tone, cinematic oversaturation, stylized filters, or AI artifacts."
    )
    sigmas = "1., 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"

    wf = {
        "1":  {"class_type": "LoadImage", "inputs": {"image": first_img}},
        "2":  {"class_type": "LoadImage", "inputs": {"image": last_img}},
        "3":  {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "4":  {"class_type": "LTXAVTextEncoderLoader", "inputs": {"text_encoder": TE, "ckpt_name": CKPT, "device": "default"}},
        "5":  {"class_type": "LTXVAudioVAELoader", "inputs": {"ckpt_name": CKPT}},
        "6":  {"class_type": "CLIPTextEncode", "inputs": {"text": text, "clip": ["4", 0]}},
        "7":  {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 0]}},
        "8":  {"class_type": "PrimitiveInt", "inputs": {"value": width}},
        "9":  {"class_type": "PrimitiveInt", "inputs": {"value": height}},
        "10": {"class_type": "PrimitiveInt", "inputs": {"value": fps}},
        # Resize first/last frames
        "11": {"class_type": "ResizeImageMaskNode", "inputs": {
            "input": ["1", 0],
            "resize_type": "scale dimensions",
            "resize_type.width": ["8", 0],
            "resize_type.height": ["9", 0],
            "resize_type.crop": "center",
            "scale_method": "nearest-exact"}},
        "12": {"class_type": "ResizeImageMaskNode", "inputs": {
            "input": ["2", 0],
            "resize_type": "scale dimensions",
            "resize_type.width": ["8", 0],
            "resize_type.height": ["9", 0],
            "resize_type.crop": "center",
            "scale_method": "nearest-exact"}},
        "13": {"class_type": "GetImageSize", "inputs": {"image": ["12", 0]}},
        "14": {"class_type": "LTXVPreprocess", "inputs": {"image": ["11", 0], "img_compression": 25}},
        "15": {"class_type": "LTXVPreprocess", "inputs": {"image": ["12", 0], "img_compression": 25}},
        "16": {"class_type": "EmptyLTXVLatentVideo", "inputs": {
            "width": ["13", 0], "height": ["13", 1], "length": frames, "batch_size": 1}},
        "17": {"class_type": "LTXVConditioning", "inputs": {
            "positive": ["6", 0], "negative": ["7", 0], "frame_rate": ["34", 0]}},
        # First-frame guide (frame_idx=0)
        "18": {"class_type": "LTXVAddGuide", "inputs": {
            "positive": ["17", 0], "negative": ["17", 1], "vae": ["3", 2],
            "latent": ["16", 0], "image": ["14", 0], "frame_idx": 0, "strength": 0.7}},
        # Last-frame guide (frame_idx=-1), latent chains from first guide
        "19": {"class_type": "LTXVAddGuide", "inputs": {
            "positive": ["18", 0], "negative": ["18", 1], "vae": ["3", 2],
            "latent": ["18", 2], "image": ["15", 0], "frame_idx": -1, "strength": 0.7}},
        # Empty audio latent
        "20": {"class_type": "LTXVEmptyLatentAudio", "inputs": {
            "frames_number": frames, "frame_rate": ["10", 0], "batch_size": 1, "audio_vae": ["5", 0]}},
        # Concat video (last guide latent) + audio
        "21": {"class_type": "LTXVConcatAVLatent", "inputs": {
            "video_latent": ["19", 2], "audio_latent": ["20", 0]}},
        "22": {"class_type": "CFGGuider", "inputs": {
            "model": ["3", 0], "positive": ["19", 0], "negative": ["19", 1], "cfg": 1.0}},
        "23": {"class_type": "SamplerEulerAncestral", "inputs": {"eta": 0.0, "s_noise": 1.0}},
        "24": {"class_type": "ManualSigmas", "inputs": {"sigmas": sigmas}},
        "25": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "26": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["25", 0], "guider": ["22", 0], "sampler": ["23", 0],
            "sigmas": ["24", 0], "latent_image": ["21", 0]}},
        "27": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["26", 0]}},
        # Crop guides on separated VIDEO latent
        "28": {"class_type": "LTXVCropGuides", "inputs": {
            "positive": ["19", 0], "negative": ["19", 1], "latent": ["27", 0]}},
        # Decode video from cropped latent
        "29": {"class_type": "VAEDecodeTiled", "inputs": {
            "samples": ["28", 2], "vae": ["3", 2],
            "tile_size": 768, "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}},
        # Decode audio from separated audio latent
        "30": {"class_type": "LTXVAudioVAEDecode", "inputs": {
            "samples": ["27", 1], "audio_vae": ["5", 0]}},
        # Convert fps int -> float (template uses expression "a")
        "34": {"class_type": "ComfyMathExpression", "inputs": {
            "expression": "a", "values.a": ["10", 0]}},
        "31": {"class_type": "CreateVideo", "inputs": {
            "images": ["29", 0], "fps": ["34", 0], "audio": ["30", 0]}},
        "32": {"class_type": "SaveVideo", "inputs": {
            "video": ["31", 0], "filename_prefix": prefix, "format": "mp4", "codec": "h264"}},
    }
    return wf

def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=60).read())

def main():
    first_img = sys.argv[1]
    last_img = sys.argv[2]
    text = sys.argv[3]
    prefix = sys.argv[4]
    width = int(sys.argv[5]) if len(sys.argv) > 5 else 768
    height = int(sys.argv[6]) if len(sys.argv) > 6 else 1344
    duration = int(sys.argv[7]) if len(sys.argv) > 7 else 5
    fps = int(sys.argv[8]) if len(sys.argv) > 8 else 24
    seed = int(sys.argv[9]) if len(sys.argv) > 9 else 1

    wf = build_workflow(first_img, last_img, text, width, height, duration, fps, seed, prefix)
    log(f"submit FLF: {first_img}->{last_img} {width}x{height} {duration}s @{fps}fps seed={seed} prefix={prefix}")
    try:
        pid = post(BASE + "/prompt", {"prompt": wf})["prompt_id"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        log(f"SUBMIT HTTP {e.code}: {body[:2000]}")
        sys.exit(1)
    except Exception as e:
        log(f"SUBMIT ERROR: {e}")
        sys.exit(1)
    log(f"prompt_id={pid}")

    t0 = time.time()
    while True:
        try:
            st = get(BASE + "/history/" + pid)
        except Exception:
            time.sleep(3)
            continue
        rec = st.get(pid)
        if not rec:
            time.sleep(3)
            continue
        status = rec.get("status", {})
        if status.get("status_str") == "error":
            log("STATUS ERROR")
            for m in status.get("messages", []):
                print("MSG:", m)
            sys.exit(1)
        if status.get("completed"):
            break
        time.sleep(3)

    out = None
    for nid, node in rec.get("outputs", {}).items():
        for name, val in node.items():
            if name in ("images", "videos") and isinstance(val, list):
                for v in val:
                    if isinstance(v, dict) and v.get("filename", "").endswith(".mp4"):
                        out = v
    if not out:
        log("NO VIDEO OUTPUT")
        sys.exit(1)

    fn = out["filename"]; sub = out.get("subfolder", "")
    url = BASE + "/view?" + urllib.parse.urlencode({"filename": fn, "subfolder": sub, "type": "output"})
    data = urllib.request.urlopen(url, timeout=120).read()
    os.makedirs("/root/reels_ltx/clips", exist_ok=True)
    dest = os.path.join("/root/reels_ltx/clips", prefix + ".mp4")
    open(dest, "wb").write(data)
    log(f"SAVED {dest} ({len(data)//1024}KB) elapsed={int(time.time()-t0)}s")

if __name__ == "__main__":
    main()
