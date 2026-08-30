# urduMovie — v2 spec, IP-Adapter (character consistency), LTX-2.5 upgrade

## 1. Season v2 spec + renderer
- **`shaheen-nagar-season1-spec.json`** = the new generation contract (from the script/PDF generator).
  Each of the 10 characters has: `character_id`, `reference_image` (`chars/<id>.png`), `name_ur/en`,
  `voice`, `vo_ur`, `style`, `negative_prompt`, and **4 `keyframes`** (`beat/prompt/camera/lighting`).
- **`render_clip_v2.py`** renders this spec (1 clip = 4 FLUX keyframes → 3×20s LTX segments → Urdu TTS → 60s music-bed merge).
  It auto-detects IP-Adapter and falls back to text-only if the node is missing.
- Run: `python render_clip_v2.py <1..10> /root/reels_urdu/out` (one at a time; LTX is sequential).

## 2. IP-Adapter — consistent characters across clips/keyframes
The `flux-ip-adapter.safetensors` weights are already on the box (`/root/ComfyUI/models/ipadapter/`),
but you must add the **node** + **clip_vision** model once (then `render_clip_v2.py` uses it automatically):

1. Install the node (restarts ComfyUI — do this between batches, not mid-render):
   ```bash
   cd /root/ComfyUI/custom_nodes
   git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
   systemctl restart comfyui
   ```
2. Add the clip_vision model for FLUX IP-Adapter into `/root/ComfyUI/models/clip_vision/`
   (the model the FLUX IP-Adapter preset expects — check the ComfyUI_IPAdapter_plus README for the
   exact file; typically the siglip/clip_vision paired with flux-ip-adapter).
3. Generate one **master portrait per character** → `/root/ComfyUI/input/chars/<id>.png`.
   Best source: pick the strongest already-rendered keyframe (`shn-XX_kf1.png`) from a finished
   batch, or run one dedicated FLUX portrait per `character_id`.
4. Verify: `render_clip_v2.py` prints `ipadapter=ON`. Every keyframe of that character then matches
   the reference likeness (weight 0.85 in `flux_keyframe`).

## 3. Upgrading to LTX-2.5 (future)
Our code is **model-agnostic at the interface**: it only changes `LTX_CKPT` + `LTX_TE`, and reuses the
same ComfyUI LTX-2 node graph (`LTXVAddGuide`, `LTXVConditioning`, AV-latent chain). To move to LTX-2.5:

1. Download the non-gated checkpoint:
   `Lightricks/LTX-2.5` (community mirror if gated) → `checkpoints/`, and its text encoder → `text_encoders/`.
   Check `gated` flag first: `curl -s https://huggingface.co/api/models/Lightricks/LTX-2.5 | grep gated`.
2. In `render_clip_v2.py` (and `render_clip.py`), point `LTX_CKPT` / `LTX_TE` at the new files.
3. LTX-2.5 adds richer modalities (audio-to-video, text-to-audio) — these surface as **additional
   ComfyUI node inputs**; the FLF path (`LTXVAddGuide`) remains backward-compatible, so start with the
   same graph, then opt into LTX-2.5 extras incrementally.
4. **Always smoke test**: 1 FLUX keyframe → 1 short LTX (97 frames) → 1 TTS, before a full batch.
5. Keep the 3×20s segmentation + `-c:v libx264` mux + `127.0.0.1` ComfyUI rules unchanged.

## 4. Instructions to give the script/PDF generator
Paste this contract so future seasons slot in with zero rework:
- Emit JSON shaped **exactly** like `shaheen-nagar-season1-spec.json`.
- **4 `keyframes` per character** (beat 1=establish, 2=develop, 3=climax, 4=resolve), each with
  `prompt` (English, one clear subject+action), `camera`, `lighting` — keep lighting/setting/wardrobe
  **identical** across the 4 beats (only action+camera change) to avoid flicker.
- Stable `character_id` + `reference_image` for every appearance of the same character.
- `style` = photorealism tokens only ("photorealistic, 8K, hyper-detailed, natural volumetric lighting…").
- `negative_prompt` = "cartoon, anime, illustration, 3d render, plastic, airbrushed, deformed, extra limbs".
- `vo_ur` = one Urdu narration string per character (UTF-8, plain, **off-screen voiceover** — avoid
  close-up talking mouths since LTX does not lip-sync).
- `voice` = one of `ur-PK-AsadNeural` | `ur-PK-UzmaNeural` | `ur-IN-GulNeural` | `ur-IN-SalmanNeural`.
