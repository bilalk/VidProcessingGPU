# render_clip.py — one urduMovie clip end-to-end (FLUX keyframes -> LTX -> Urdu TTS -> merge).
# Runs ON the GPU server (ComfyUI at 127.0.0.1:8188). Urdu VO text comes from the clip's "vo_ur".
import json, os, sys, time, subprocess, urllib.request, urllib.parse

BASE = "http://127.0.0.1:8188"
FPS = 24
CLIP_SEC = 60
FLUX_CKPT = "flux1-dev.safetensors"
FLUX_CLIP1 = "t5xxl_fp8_e4m3fn.safetensors"
FLUX_CLIP2 = "clip_l.safetensors"
FLUX_VAE = "ae.safetensors"
LTX_CKPT = "ltx-2.3-22b-distilled-1.1.safetensors"
LTX_TE = "gemma_3_12B_it_fp4_mixed.safetensors"
LTX_FPS = 24
NEG = ("blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, "
       "excessive noise, grainy texture, poor lighting, flickering, motion blur, distorted proportions, "
       "unnatural skin tones, deformed facial features, extra limbs, disfigured hands, artifacts around text, "
       "unreadable text, inconsistent perspective, camera shake, incorrect depth of field, background clutter, "
       "jittery movement, awkward pauses, unnatural transitions, tilted camera, stylized filters, or AI artifacts.")
SIGMAS = "1., 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
os.makedirs(WORK, exist_ok=True)
INPUT = "/root/ComfyUI/input"   # LoadImage reads from here
os.makedirs(INPUT, exist_ok=True)


def post(path, data):
    r = urllib.request.Request(BASE + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=120).read())


def poll(prompt_id):
    while True:
        h = json.loads(urllib.request.urlopen(BASE + f"/history/{prompt_id}", timeout=60).read())
        rec = h.get(prompt_id)
        if rec and rec.get("status", {}).get("completed"):
            return rec
        if rec and rec.get("status", {}).get("status_str") == "error":
            raise RuntimeError("ComfyUI error")
        time.sleep(3)


def flux_keyframe(prompt, seed, out_png):
    node_prompt = prompt + ", cinematic film still, vertical composition"
    g = {
        "11": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": FLUX_CLIP1, "clip_name2": FLUX_CLIP2, "type": "flux"}},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": FLUX_CKPT}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": node_prompt, "clip": ["11", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["11", 0]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 1344, "batch_size": 1}},
        "3": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 16, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAELoader", "inputs": {"vae_name": FLUX_VAE}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["8", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": out_png}},
    }
    pid = post("/prompt", {"prompt": g})["prompt_id"]
    rec = poll(pid)
    for nid, outn in rec["outputs"].items():
        for img in outn.get("images", []):
            if img.get("filename", "").endswith(".png"):
                return img["filename"], img.get("subfolder", "")


def fetch_image(filename, subfolder, dest):
    url = BASE + "/view?" + urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": "output"})
    open(dest, "wb").write(urllib.request.urlopen(url, timeout=120).read())
    return dest


def ltx_animate(start_png, end_png, out_mp4, motion, width, height, length_frames, seed):
    """Exact proven LTX-2.3 First/Last-Frame graph (from scripts/ltx_29.py flf_workflow)."""
    g = {
        "1": {"class_type": "LoadImage", "inputs": {"image": start_png}},
        "2": {"class_type": "LoadImage", "inputs": {"image": end_png}},
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": LTX_CKPT}},
        "4": {"class_type": "LTXAVTextEncoderLoader", "inputs": {"text_encoder": LTX_TE, "ckpt_name": LTX_CKPT, "device": "default"}},
        "5": {"class_type": "LTXVAudioVAELoader", "inputs": {"ckpt_name": LTX_CKPT}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": motion, "clip": ["4", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 0]}},
        "8": {"class_type": "PrimitiveInt", "inputs": {"value": width}},
        "9": {"class_type": "PrimitiveInt", "inputs": {"value": height}},
        "10": {"class_type": "PrimitiveInt", "inputs": {"value": LTX_FPS}},
        "11": {"class_type": "ResizeImageMaskNode", "inputs": {"input": ["1", 0], "resize_type": "scale dimensions", "resize_type.width": ["8", 0], "resize_type.height": ["9", 0], "resize_type.crop": "center", "scale_method": "nearest-exact"}},
        "12": {"class_type": "ResizeImageMaskNode", "inputs": {"input": ["2", 0], "resize_type": "scale dimensions", "resize_type.width": ["8", 0], "resize_type.height": ["9", 0], "resize_type.crop": "center", "scale_method": "nearest-exact"}},
        "13": {"class_type": "GetImageSize", "inputs": {"image": ["12", 0]}},
        "14": {"class_type": "LTXVPreprocess", "inputs": {"image": ["11", 0], "img_compression": 25}},
        "15": {"class_type": "LTXVPreprocess", "inputs": {"image": ["12", 0], "img_compression": 25}},
        "16": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": ["13", 0], "height": ["13", 1], "length": length_frames, "batch_size": 1}},
        "34": {"class_type": "ComfyMathExpression", "inputs": {"expression": "a", "values.a": ["10", 0]}},
        "17": {"class_type": "LTXVConditioning", "inputs": {"positive": ["6", 0], "negative": ["7", 0], "frame_rate": ["34", 0]}},
        "18": {"class_type": "LTXVAddGuide", "inputs": {"positive": ["17", 0], "negative": ["17", 1], "vae": ["3", 2], "latent": ["16", 0], "image": ["14", 0], "frame_idx": 0, "strength": 0.7}},
        "19": {"class_type": "LTXVAddGuide", "inputs": {"positive": ["18", 0], "negative": ["18", 1], "vae": ["3", 2], "latent": ["18", 2], "image": ["15", 0], "frame_idx": -1, "strength": 0.7}},
        "20": {"class_type": "LTXVEmptyLatentAudio", "inputs": {"frames_number": length_frames, "frame_rate": ["10", 0], "batch_size": 1, "audio_vae": ["5", 0]}},
        "21": {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["19", 2], "audio_latent": ["20", 0]}},
        "22": {"class_type": "CFGGuider", "inputs": {"model": ["3", 0], "positive": ["19", 0], "negative": ["19", 1], "cfg": 1.0}},
        "23": {"class_type": "SamplerEulerAncestral", "inputs": {"eta": 0.0, "s_noise": 1.0}},
        "24": {"class_type": "ManualSigmas", "inputs": {"sigmas": SIGMAS}},
        "25": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "26": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["25", 0], "guider": ["22", 0], "sampler": ["23", 0], "sigmas": ["24", 0], "latent_image": ["21", 0]}},
        "27": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["26", 0]}},
        "28": {"class_type": "LTXVCropGuides", "inputs": {"positive": ["19", 0], "negative": ["19", 1], "latent": ["27", 0]}},
        "29": {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["28", 2], "vae": ["3", 2], "tile_size": 768, "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}},
        "30": {"class_type": "LTXVAudioVAEDecode", "inputs": {"samples": ["27", 1], "audio_vae": ["5", 0]}},
        "31": {"class_type": "CreateVideo", "inputs": {"images": ["29", 0], "fps": ["34", 0], "audio": ["30", 0]}},
        "32": {"class_type": "SaveVideo", "inputs": {"video": ["31", 0], "filename_prefix": out_mp4, "format": "mp4", "codec": "h264"}},
    }
    pid = post("/prompt", {"prompt": g})["prompt_id"]
    rec = poll(pid)
    for nid, outn in rec["outputs"].items():
        for v in outn.get("videos", []):
            return v["filename"], v.get("subfolder", "")


def tts_urdu(text, voice, out_file):
    import asyncio, edge_tts
    asyncio.run(edge_tts.Communicate(text, voice).save(out_file))
    return out_file


def merge(video_path, audio_path, out_path):
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-i", audio_path,
                    "-c:v", "libx264", "-c:a", "aac", "-shortest", out_path],
                   check=True, capture_output=True)
    return out_path


def render_clip(clip, out_dir):
    cid = clip["id"]
    v = clip["visual"]
    start_prompt = v["prompt"] + ", wide establishing shot, calm beginning moment"
    end_prompt = v["prompt"] + ", " + v["camera_motion"] + ", dramatic final moment"
    seed = clip["index"] * 1000
    s_name, s_sub = flux_keyframe(start_prompt, seed, f"{cid}_start")
    e_name, e_sub = flux_keyframe(end_prompt, seed + 1, f"{cid}_end")
    s_png = fetch_image(s_name, s_sub, os.path.join(INPUT, f"{cid}_start.png"))
    e_png = fetch_image(e_name, e_sub, os.path.join(INPUT, f"{cid}_end.png"))
    print(f"[{cid}] keyframes done")
    v_name, v_sub = ltx_animate(f"{cid}_start.png", f"{cid}_end.png", f"{cid}_anim", v["camera_motion"], 768, 1344, CLIP_SEC * LTX_FPS, seed)
    vid = fetch_image(v_name, v_sub, os.path.join(WORK, f"{cid}_anim.mp4"))
    print(f"[{cid}] LTX done -> {vid}")
    wav = tts_urdu(clip["vo_ur"], "ur-PK-AsmaNeural", os.path.join(WORK, f"{cid}_vo.mp3"))
    print(f"[{cid}] Urdu TTS done")
    final = merge(vid, wav, os.path.join(out_dir, f"{cid}.mp4"))
    print(f"[{cid}] FINAL -> {final}")
    return final


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    movie = json.load(open(os.path.join(here, "movie.json"), encoding="utf-8"))
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "/root/reels_urdu/out"
    os.makedirs(out_dir, exist_ok=True)
    clip = next(c for c in movie["clips"] if c["index"] == idx)
    if clip["vo_ur"].startswith("TODO"):
        print(f"[{clip['id']}] WARNING: vo_ur still TODO — fill Urdu narration before running")
    render_clip(clip, out_dir)

