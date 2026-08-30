# urduMovie — "Shaheen Nagar" (شاہین نگر)

New branch (`urduMovie`) for rendering **10 × 1-minute Urdu cinematic clips** from a single JSON,
rendered with FLUX (start/end keyframes) + LTX-2.3 (First/Last-Frame animation) + Urdu TTS.

> This branch is **self-contained**. It does NOT touch the `BranchAug29` web app (`:5000`) or the
> GPU status page (`:80`). Those live only on the other branch.

## Files
- `movie.json` — the single source of truth. 10 clips (characters), each with:
  - `name_en` / `name_ur` — character name (English filled; **Urdu = TODO**)
  - `vo_ur` — the Urdu narration line to be spoken (**TODO — fill these 10 lines**)
  - `visual.prompt` — the English cinematic description (extracted from the PDF)
  - `visual.shot_type` / `camera_motion` / `lighting` — from the PDF
  - `duration_sec` = 60
- `render_clip.py` — renders ONE clip end-to-end (FLUX + LTX + TTS + merge)
- `work/` — intermediate keyframes / VO / merged anims (gitignored)

## How start/end images are decided (intelligently)
For each clip, `render_clip.py` derives TWO FLUX keyframes from the single visual prompt:
- **start** = `prompt + "wide establishing shot, calm beginning moment"`
- **end**   = `prompt + "<camera_motion>, dramatic final moment"`

Then LTX-2.3 animates first-frame → last-frame over the clip's full duration, driven by the
`camera_motion` as the LTX motion prompt. This matches the PDF's per-character `Camera` directive.

## What you still need to fill (before a real run)
1. `movie.json` → `name_ur` (10 Urdu names) and `vo_ur` (10 Urdu narration lines).
2. Optionally a `music` field per clip (background bed) — not wired yet.

## Run (on the GPU server)
```bash
scp -r urdu_movie root@GPU:/root/reels_urdu/
ssh root@GPU "cd /root/reels_urdu && /root/ComfyUI/venv/bin/python render_clip.py <1..10> /root/reels_urdu/out"
```
Process clips **one at a time** (LTX is sequential — do not burst the queue). Then pull results:
```bash
scp root@GPU:/root/reels_urdu/out/shN-*.mp4 .
```

## TODO / notes
- 60 s clip = `length = 60 * 24 = 1440` frames in one LTX pass. LTX may need **segmented**
  generation (e.g. 3×20s chunks) or the temporal upscaler for clean 60s output — tune `CLIP_SEC`
  / `length_frames` in `render_clip.py` after a first smoke test.
- Urdu voices: `ur-PK-AsmaNeural` (F), `ur-PK-AsadNeural` (M), `ur-PK-UzmaNeural` (F) — valid on edge-tts.
- `video-only` LTX is hinted at in the PDF; audio (Urdu VO) is merged by `ffmpeg` (not spkg as LTX audio-VAE).
