# urduMovie RESUME — "Shaheen Nagar" (شاہین نگر) Urdu cinematic clips

Branch: **`urduMovie`** · GPU: **`134.199.207.48`** · SSH: `ssh -i aug30 root@134.199.207.48`

This branch is **self-contained** — it does NOT touch `BranchAug29`, the `:5000` web app, or the
GPU status page. It renders 10 × 1-minute Urdu cinematic clips from one JSON.

---

## 1. Current state (what's done)
- Pipeline **works end-to-end** (FLUX → LTX-2.3 → Urdu TTS → 60s music-bed merge).
- `shn-01.mp4` (Markhor) rendered + delivered (60s, 9:16). Clips 2–10 render **sequentially** via
  `/root/reels_urdu/render_all.sh` (background).
- Check progress:
  ```bash
  ssh -i aug30 root@134.199.207.48 "tail -8 /root/reels_urdu/render_all.log"
  ssh -i aug30 root@134.199.207.48 "ls /root/reels_urdu/out/"
  ```

## 2. Resume steps (a new agent can do this)
```bash
git clone https://github.com/bilalk/VidProcessingGPU
git checkout urduMovie
scp urdu_movie/{movie.json,render_clip.py} root@134.199.207.48:/root/reels_urdu/
# render remaining clips (or one clip):
ssh root@134.199.207.48 "cd /root/reels_urdu && bash render_all.sh"         # 2..10
ssh root@134.199.207.48 "cd /root/reels_urdu && /root/ComfyUI/venv/bin/python -u render_clip.py 3 /root/reels_urdu/out"
# download finished clips:
scp root@134.199.207.48:/root/reels_urdu/out/*.mp4 .
```

## 3. Pipeline architecture
- **`movie.json`** = single source. 10 clips, each: `name_ur`, `vo_ur` (Urdu narration), `voice`
  (per-character), `visual.prompt` (English), `shot_type`, `camera_motion`, `lighting`,
  `duration_sec=60`.
- **`render_clip.py`** per clip: 4 FLUX keyframes → 3 LTX First/Last-Frame segments (20s each) →
  concat → Urdu edge-tts TTS → ffmpeg merge (VO + music bed, full 60s).
- Keyframes = progressive prompts (establish → develop → climax → resolve) from `visual.prompt` +
  `camera_motion`. LTX uses the proven `flf_workflow` graph (`LTXVAddGuide` first/last frames).

## 4. Models (all **non-gated** — NO HF token)
| File | Source |
|---|---|
| `flux1-dev.safetensors` | `Comfy-Org/flux1-dev` |
| `ltx-2.3-22b-distilled-fp8.safetensors` | (already on box; `-dev` = largest but needs non-distilled sampler) |
| `gemma_3_12B_it_fp4_mixed.safetensors` | `eraRelentless/Gemma_3_12B_it_fp4` |
| `t5xxl_fp8_e4m3fn.safetensors` + `clip_l.safetensors` | `comfyanonymous/flux_text_encoders` |
| `ae.safetensors` | `foxmail/flux_vae` |
| `bed.wav` (180s music) | `/root/reels_r3/bed.wav` (copy from a warm box) |

Download: `curl -fL -C - -o <dest> https://huggingface.co/<REPO>/resolve/main/<FILE>`

## 5. Urdu voices (edge-tts, all valid)
`ur-PK-AsadNeural` (M) · `ur-PK-UzmaNeural` (F) · `ur-IN-GulNeural` (F) · `ur-IN-SalmanNeural` (M).
⚠️ `ur-PK-AsmaNeural` **does NOT exist** (caused `NoAudioReceived`).

## 6. Security — this box was cryptominer-compromised before. Keep it locked.
- UFW: `default deny incoming`; allow only 22/80/443/3389; block C2 `103.249.201.108` in+out.
- SSH: `PermitRootLogin prohibit-password` (key-only), single key `aug30`.
- `miner_guard.sh` cron every 10 min (kills miner sigs + droppers).
- **NEVER** run ComfyUI with `--listen 0.0.0.0` (that is exactly how the miner got in → use
  `127.0.0.1`). Re-apply all of this on any fresh box.

## 7. Mistakes already hit — do NOT repeat
1. Gated HF repos (`black-forest-labs/FLUX.1-dev`, Lightricks `LTX-Video`) → HTTP 401. Use non-gated mirrors (§4).
2. `ur-PK-AsmaNeural` → `NoAudioReceived`. Use §5 voices.
3. `ffmpeg -shortest` truncated 60s → 34s (VO length). Now full 60s with music bed.
4. LTX `SaveVideo`/`CreateVideo` output type = `VIDEO` (not key `videos`); detect by `.mp4` filename.
5. 480-frame (20s) LTX segments work on 205 GB VRAM (no OOM).
6. `134.199.196.177` (other box) went down; **this branch runs on `134.199.207.48`**.

## 8. From-scratch GPU install (new box)
1. Provision blank AMD MI300X droplet.
2. Install ComfyUI 0.3x + venv + deps (`github.com/comfyanonymous/ComfyUI`, see `docs/GPU_SETUP.md`).
3. Download the 6 models from §4 (non-gated `curl` one-liners).
4. `scp urdu_movie/*` + copy `bed.wav`.
5. Harden per §6 (UFW + SSH + miner_guard + `127.0.0.1`).
6. Smoke test: 1 FLUX keyframe → 1 short LTX (97 frames) → 1 Urdu TTS, then run clip 1.
