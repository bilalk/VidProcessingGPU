# PromptForAgentNew — run a fresh 12-reel batch (OLD 4-panel ~60s pipeline) on a NEW client + NEW GPU

You are a coding agent. Your job: take this repo and two JSON manifest files, stand up
the pipeline on a **fresh Windows client + blank AMD GPU server**, and generate a
**12-reel FLUX round, then a LTX round**, using the **OLD full 4-panel (~60s) method**.
Number videos **from 0 onward** (this is a separate setup — do NOT reuse any ids from
other machines; start clean).

---

## 1. What to download / where things are

Git repo (authoritative code): `https://github.com/bilalk/VidProcessingGPU`
```
git clone https://github.com/bilalk/VidProcessingGPU
```
Repo map:
- `pipeline/flux/`  → FLUX round (OLD format): `tts_gen3.py`, `flux_gen_opt.py`, `assemble5.py`, `gen_bed_r3.py`, `run_dual.sh`, `launch_dual.sh`
- `pipeline/ltx_v3/` → LTX round (OLD FLF): `run_ltx_v3.py` (+ `ltx_flf_gen.py`, `run_ltx_full.py`)
- `pipeline/v2/`   → NEW single-scene format (IGNORE for this task — not used here)
- `scripts/`       → GPU setup + renumber + verify + patch helpers
- `manifests/old/` → example OLD-format JSONs
- `docs/`          → `ARCHITECTURE.md`, `GPU_SETUP.md`, `JSON_FORMATS.md`, `RESUME_GUIDE_R4.md`

**Read first (in order):** `README.md` → `docs/GPU_SETUP.md` → `docs/JSON_FORMATS.md` → `docs/RESUME_GUIDE_R4.md`.

The two JSON files I will give you use the **OLD 4-panel schema** (# of reels = 12 total,
6 channels × 2). Their exact shape is described in `docs/JSON_FORMATS.md` §"OLD format".

---

## 2. Windows client setup

- Install **Git**, **Python 3.11+**, and an **SSH client** (OpenSSH is built into Windows 10/11).
- Copy your GPU **SSH private key** to `C:\Users\<you>\.ssh\id_newgpu` (or any path you choose).
- Put the two JSON manifests + this repo on the client, e.g. `C:\ProjectComfy\`.

Workflow direction (thin client):
- Client: manifests + orchestration + result storage.
- Server: all compute (FLUX stills → LTX video → TTS voice → ffmpeg assembly), driven by ComfyUI.

---

## 3. GPU server setup (blank AMD MI300X)

Follow `docs/GPU_SETUP.md` exactly:
1. `scp scripts/setup_new_gpu2.sh root@GPU:/root/ && ssh root@GPU "bash /root/setup_new_gpu2.sh"` — installs venv, PyTorch ROCm 7.2, ComfyUI, RDP, fonts, `comfyui.service`.
2. Download models into `/root/ComfyUI/models/` (list + sizes in `GPU_SETUP.md`): `ltx-2.3-22b-distilled-fp8`, `gemma_3_12B_it_fp4_mixed`, `flux1-dev`, `t5xxl_fp8`, `clip_l`, `ae`.
3. Deploy code:
   ```
   scp pipeline/flux/*  root@GPU:/root/reels_r3/
   scp pipeline/ltx_v3/*.py root@GPU:/root/reels_ltx/
   ```
4. Verify: `ssh root@GPU "systemctl is-active comfyui && curl -s http://127.0.0.1:8188/system_stats"`.

> ⚠️ Use `http://127.0.0.1:8188`, NEVER `localhost`.

---

## 4. Prepare the two JSONs (renumber from 0)

Both input files reuse ids `025/026` + seeds `41001–41012`. **Renumber to fresh ids starting at 0** so there is no cache/id collision, then verify + push.

```bash
# adapt scripts/renumber_aug28.py: set start_id = 0 for file 1, 12 for file 2
python scripts/renumber_aug28.py      # -> manifest_a.json (ids 000-011), manifest_b.json (012-023)
python scripts/verify_aug28.py        # confirm 12 reels, 6 channels, no orientation errors
scp manifest_a.json manifest_b.json root@GPU:/root/reels_r3/
```

Correct 6 channels: `arabic-to-english, chinese-to-english, english-to-arabic, english-to-chinese, english-to-spanish, spanish-to-english`.
If any `english-to-X` reel has `src` in the foreign language (and `tgt` English), run `scripts/fix_srctgt.py`.

---

## 5. FLUX round (OLD 4-panel, mobile), then review

```bash
ssh root@GPU "cd /root/reels_r3 && setsid ./run_dual.sh manifest_a.json manifest_b.json > logs/run.log 2>&1 < /dev/null &"
```
- Phase 1: parallel TTS + FLUX burst (all stills on one ComfyUI queue).
- Phase 2: music bed; Phase 3: SEQUENTIAL assembly (ffmpeg).
- Output: `/root/reels_r3/out/<channel>/<id>.mp4` (mobile 1080×1920, ~55–65s each).
- Pull a couple to the client and show the user; wait for approval before LTX.

## 6. LTX round (OLD FLF, ~60s, mobile + desktop), one channel at a time

```bash
# for each of the 6 channels:
ssh root@GPU "cd /root/reels_ltx && setsid python run_ltx_v3.py <channel> /root/reels_r3/manifest_a.json > logs/ch.log 2>&1 &"
```
- LTX-2.3 animates between the 4 FLUX keyframes (First/Last-Frame) → 3 clips + 1 recap panel.
- Output: `/root/reels_ltx/out_v3_mobile/` + `out_v3_desktop/` (true 16:9).
- Pull results to the client for review.

---

## 7. Hard rules (violating these wastes hours)

1. `127.0.0.1:8188`, never `localhost`.
2. No `pkill -f` over SSH — use PIDs.
3. Long work via `setsid … > log 2>&1 < /dev/null &`, then poll the log.
4. ONE scp stream at a time.
5. ComfyUI queue ≤ ~50 jobs → LTX is channel-by-channel; FLUX bursts ≤ ~96.
6. Final mux uses `-c:v libx264`, never `-c:v copy`.
7. Never `apt autoremove` / reinstall packages / redownload models.
8. Renumber every batch to fresh ids.

## 8. Definition of done
- FLUX round: 12 mobile videos, 0 errors, reviewed OK.
- LTX round: 12 reels × (mobile + desktop), 0 errors, pulled to client.
- Write a resume `.md` (like `docs/RESUME_Aug28.md`) recording the new server IP, ids used, and
  next steps, so any future agent can resume without re-discovery.
