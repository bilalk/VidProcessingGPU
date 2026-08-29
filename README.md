# VidProcessingGPU — REEL FACTORY

Automated **AI video-generation pipelines** for bilingual "reels" / short dramatic skits. Thin **Windows client** + **AMD Instinct MI300X GPU server** (ComfyUI). Produces 9:16 mobile + 16:9 desktop videos.

> **Self-serve web UI (new, on `BranchAug29`):** see `PromptForAgentNew.md` + `webapp/`. A Flask web service (Windows, port `:5000`) orchestrates the pipeline end-to-end — upload 2 JSONs, it validates / dedups / renumbers / runs FLUX (+LTX) / pulls results — and mirrors live progress on the GPU status page (port `:80`). Use it instead of the manual ssh/scp steps in §5 below.

---

## 1. Architecture (high level)

```
WINDOWS CLIENT                     AMD GPU SERVER (Linux, Ubuntu 24.04)
----------------                   -----------------------------------
manifest JSON (content)  --scp-->  /root/reels_r3/  (workspace)
orchestrator scripts    --scp-->  FLUX.1-dev (stills)  ┐
result videos          <--scp--   LTX-2.3 (video)      ┼ ComfyUI (http://127.0.0.1:8188)
                                  edge-tts (voice)     │
                                  ffmpeg (assembly)    ┘
```

- **Client is thin** — content + orchestration + results. All compute is on the GPU server.
- **Server scripts are manifest-driven** — same code processes any valid JSON.
- Glued with plain Python (`urllib` → ComfyUI REST, `subprocess` → ffmpeg/edge-tts) and bash.

---

## 2. Repo layout

| Path | Purpose |
|---|---|
| `pipeline/flux/` | **OLD-format** FLUX pipeline (4-panel stills + Ken Burns + subtitles + TTS) |
| `pipeline/ltx_v3/` | **OLD-format** LTX pipeline (FLF animation between 4 keyframes, ~60s) |
| `pipeline/v2/` | **NEW-format** pipeline (single-scene I2V skits, ~7-9s) |
| `scripts/` | GPU setup, model transfer, renumber, verify, patch helpers |
| `manifests/old|new|renumbered/` | Example manifests per JSON format |
| `docs/` | Architecture + resume guides + setup + JSON reference |

---

## 3. GPU setup (summary — full detail in `docs/GPU_SETUP.md`)

From a **blank MI300X droplet** (DigitalOcean devcloud):

1. SSH in as `root` with an SSH key.
2. Run **`scripts/setup_new_gpu2.sh`** — installs Python 3.12 venv (`/root/ComfyUI/venv`), PyTorch 2.13+rocm7.2, ComfyUI (`/root/ComfyUI`) + deps, xrdp, Noto CJK/Arabic fonts, `comfyui.service` (systemd, `--listen 0.0.0.0 --port 8188 --highvram`).
3. Download models into `/root/ComfyUI/models/` (see `scripts/transfer.sh` for server→server copy; else HuggingFace):
   - `checkpoints/ltx-2.3-22b-distilled-fp8.safetensors` (~29.5 GB)
   - `text_encoders/gemma_3_12B_it_fp4_mixed.safetensors` (~9.4 GB)
   - `checkpoints/flux1-dev.safetensors` (~23 GB) + `t5xxl_fp8_e4m3fn.safetensors` + `clip_l.safetensors` + `vae/ae.safetensors`
4. Push pipeline scripts + a manifest to `/root/reels_r3/` via scp.

> ⚠️ Always use `http://127.0.0.1:8188` (NOT `localhost`) from the server.

---

## 4. Two JSON formats (full detail in `docs/JSON_FORMATS.md`)

### OLD format (longer ~60s clips) — `pipeline/flux/` + `pipeline/ltx_v3/`
```json
{ "reels": [ { "id":"ar-en-025", "channel":"arabic-to-english", "pair":"ar-en",
  "topic":"...", "seed":41001,
  "voice_src":"ar-SA-ZariyahNeural", "voice_tgt":"en-US-JennyNeural",
  "words":[ {"src":"همس","tgt":"whisper","translit":"hams"}, ... 3 total ],
  "lines":[ {"src":"...","tgt":"...","translit":"..."}, ... 3 total ],
  "scenes":[ "prompt ...", "prompt ...", "prompt ...", "prompt ..." ] } ] }
```
- FLUX generates 4 stills → LTX animates **between** them (First/Last-Frame) → 3 clips + 1 recap panel.

### NEW format (short ~7-9s skits) — `pipeline/v2/`
```json
{ "reels": [ { "id":"ar-en-100", "channel":"arabic-to-english", "pair":"ar-en",
  "topic":"...", "seed":51000,
  "voice_src":"...", "voice_tgt":"...", "voice_src2":"...", "voice_tgt2":"...",
  "words":[ "أين", "جوازي", "Where", "passport" ],
  "lines":[ {"id":1,"speaker":"voice_src2","text":"...","start":0.0,"end":2.5},
            {"id":2,"speaker":"voice_tgt","text":"...","start":2.6,"end":5.5} ],
  "scenes":[ {"scene_id":1,"start_time":0.0,"end_time":5.5,"image_prompt":"...","motion":"ken_burns_...","audio_sync":"..."} ] } ] }
```
- One FLUX still → LTX **image-to-video** (I2V) → single animated clip.

---

## 5. Running the pipeline

### 5a. OLD format (parallel 2-JSON, longer clips)
```bash
# local: renumber the two input JSONs to unique ids (avoids cache/id collisions)
python scripts/renumber_aug28.py

# push to server
scp manifest_*.json root@GPU:/root/reels_r3/

# FLUX round (parallel TTS + FLUX on one queue, SEQUENTIAL assembly)
ssh root@GPU "cd /root/reels_r3 && setsid ./run_dual.sh manifest_a.json manifest_b.json > logs/run.log 2>&1 < /dev/null &"

# LTX round (ONE channel at a time — avoids ComfyUI queue wipe)
ssh root@GPU "cd /root/reels_ltx && setsid python run_ltx_v3.py <channel> /root/reels_r3/manifest.json > logs/ch.log 2>&1 &"
# channels: arabic-to-english, chinese-to-english, english-to-arabic, english-to-chinese, english-to-spanish, spanish-to-english
```

### 5b. NEW format (single-skits)
```bash
python scripts/renumber_100.py           # test.json -> ids 100+
scp manifests/... root@GPU:/root/reels_r3/
ssh root@GPU "cd /root/reels_r3 && python tts_v2.py manifest.json"        # TTS
ssh root@GPU "cd /root/reels_r3 && python flux_v2.py manifest.json"       # FLUX stills
ssh root@GPU "cd /root/reels_r3 && python assemble_v2.py manifest.json"   # Ken Burns assemble (FLUX preview)
ssh root@GPU "cd /root/reels_ltx2 && python ltx_v2.py"                    # LTX I2V + assemble (mobile+desktop)
```

---

## 6. Critical / hard-won rules

1. Use `127.0.0.1:8188`, never `localhost`.
2. **No `pkill -f` over SSH** — use specific PIDs.
3. Long work via `setsid … > log 2>&1 < /dev/null &`, then poll the log.
4. ONE scp stream at a time (parallel scp collapses the link).
5. ComfyUI queue ≤ ~50 jobs (soft-restart wipes queue). LTX = channel-by-channel; FLUX burst-submits ≤ ~96.
6. Final mux MUST use `-c:v libx264`, never `-c:v copy` (corrupts h264 on this ffmpeg).
7. Never `apt autoremove` / reinstall packages / redownload models.
8. Renumber manifests to **fresh ids** every batch (stale cache keyed by id silently reuses old content).
9. For `english-to-X` reels, `src` must be English (`scripts/fix_srctgt.py` fixes the common inversion bug).

---

## 7. Resume / continuity

- **`docs/RESUME_Aug28.md`** — current state + exact next steps (read first when resuming).
- **`docs/RESUME_GUIDE_R4.md`** — master resumption guide (connection, rules, file layout).
- **`docs/ARCHITECTURE.md`** — full architecture (tech stack, flows, LTX-2.3 §F, prompt-split §E).
- **`docs/GPU_SETUP.md`** — step-by-step GPU provisioning.
- **`docs/JSON_FORMATS.md`** — detailed schema reference for both formats.

A fresh agent should read, in order: `README.md` → `docs/RESUME_Aug28.md` → `docs/ARCHITECTURE.md` → act.

