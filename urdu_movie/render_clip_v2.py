# render_clip_v2.py — season-spec renderer (character_id + reference_image + style + 4 keyframes) + optional IP-Adapter.
# Reads shaheen-nagar-season1-spec.json. Reuses the proven FLUX/LTX/TTS/merge engine from render_clip.py.
import json, os, sys, urllib.request
from render_clip import (BASE, FLUX_CKPT, FLUX_CLIP1, FLUX_CLIP2, FLUX_VAE, LTX_CKPT, LTX_TE,
                         LTX_FPS, SEG_SEC, BED, INPUT, WORK, NEG,
                         post, poll, fetch_image, ltx_animate, tts_urdu, concat_videos, merge)

IPA_MODEL = "flux-ip-adapter.safetensors"
_ipa = None


def has_ipadapter():
    """True when the XLabs FLUX IP-Adapter path is ready (nodes + fp8 model + refs)."""
    global _ipa
    if _ipa is None:
        try:
            oi = json.loads(urllib.request.urlopen(BASE + "/object_info", timeout=90).read())
            _ipa = all(n in oi for n in ("LoadFluxIPAdapter", "ApplyFluxIPAdapter", "XlabsSampler"))
        except Exception:
            _ipa = False
    return _ipa


def flux_keyframe(prompt, style, negative, seed, refname, prefix):
    """XLabs FLUX generation with optional IP-Adapter (reference image locks character)."""
    pos = (prompt + ", " + style).strip(", ") + ", cinematic film still, vertical composition"
    neg = (negative + ", " + NEG) if negative else NEG
    g = {
        "10": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev-fp8.safetensors", "weight_dtype": "fp8_e4m3fn"}},
        "4":  {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": FLUX_CLIP1, "clip_name2": FLUX_CLIP2, "type": "flux"}},
        "6":  {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["4", 0], "clip_l": pos, "t5xxl": pos, "guidance": 3.5}},
        "7":  {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["4", 0], "clip_l": neg, "t5xxl": neg, "guidance": 3.5}},
        "5":  {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 1344, "batch_size": 1}},
        "3":  {"class_type": "XlabsSampler", "inputs": {"model": ["MODEL", 0], "conditioning": ["6", 0], "neg_conditioning": ["7", 0], "noise_seed": seed, "steps": 25, "timestep_to_start_cfg": 0, "true_gs": 3.5, "image_to_image_strength": 1.0, "denoise_strength": 1.0, "latent_image": ["5", 0]}},
        "8":  {"class_type": "VAELoader", "inputs": {"vae_name": FLUX_VAE}},
        "9":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["8", 0]}},
        "36": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }
    model_src = ["10", 0]
    if refname and has_ipadapter():
        g["16"]  = {"class_type": "LoadImage", "inputs": {"image": refname}}
        g["32"]  = {"class_type": "LoadFluxIPAdapter", "inputs": {"ipadatper": "flux-ip-adapter.safetensors", "clip_vision": "model.safetensors", "provider": "GPU"}}
        g["27"]  = {"class_type": "ApplyFluxIPAdapter", "inputs": {"model": ["10", 0], "ip_adapter_flux": ["32", 0], "image": ["16", 0], "ip_scale": 0.92}}
        model_src = ["27", 0]
    g["3"]["inputs"]["model"] = model_src
    pid = post("/prompt", {"prompt": g})["prompt_id"]
    rec = poll(pid)
    for nid, outn in rec.get("outputs", {}).items():
        for img in outn.get("images", []):
            if img.get("filename", "").endswith(".png"):
                return img["filename"], img.get("subfolder", "")
    return None, None


def render_character(char, seed, out_dir):
    cid = char["character_id"]
    voice = char["voice"]
    style = char.get("style", "")
    negative = char.get("negative_prompt", "")
    ref = os.path.basename(char.get("reference_image", "") or "")
    kfs = char["keyframes"]
    for i, kf in enumerate(kfs):
        prompt = kf["prompt"] + ", " + kf.get("lighting", "")
        nm, sub = flux_keyframe(prompt, style, negative, seed + i, ref, f"{cid}_kf{i+1}")
        fetch_image(nm, sub, os.path.join(INPUT, f"{cid}_kf{i+1}.png"))
    print(f"[{cid}] 4 keyframes done (ipadapter={'ON' if has_ipadapter() else 'OFF'})")
    frames = SEG_SEC * LTX_FPS
    segs = []
    for s in range(3):
        camera = kfs[s]["camera"]
        nm, sub = ltx_animate(f"{cid}_kf{s+1}.png", f"{cid}_kf{s+2}.png", f"{cid}_seg{s+1}",
                              camera, 768, 1344, frames, seed + 100 + s)
        segs.append(fetch_image(nm, sub, os.path.join(WORK, f"{cid}_seg{s+1}.mp4")))
        print(f"[{cid}] segment {s+1}/3 done")
    anim = concat_videos(segs, os.path.join(WORK, f"{cid}_anim.mp4"))
    wav = tts_urdu(char["vo_ur"], voice, os.path.join(WORK, f"{cid}_vo.mp3"))
    final = merge(anim, wav, BED, os.path.join(out_dir, f"{cid}.mp4"), 60)
    print(f"[{cid}] FINAL -> {final}")
    return final


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    spec = json.load(open(os.path.join(here, "shaheen-nagar-season1-spec.json"), encoding="utf-8"))
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "/root/reels_urdu/out"
    os.makedirs(out_dir, exist_ok=True)
    char = spec[idx - 1]
    print(f"rendering clip {idx}: {char['character_id']} ({char['name_en']})")
    render_character(char, 1000 * idx, out_dir)
