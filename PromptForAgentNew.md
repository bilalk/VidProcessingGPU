# PromptForAgentNew — stand up the self-serve REEL FACTORY (web UI `:5000` + AMD GPU)

You are a coding agent. From this repo alone, stand up a **self-serve web UI** on a Windows client that drives the **OLD ~60s 4-panel pipeline** on an AMD Instinct MI300X GPU server. After the one-time setup below, the owner uploads **two JSON manifests in a browser, clicks Start**, and watches live progress on **both** the client page (`:5000`) and the GPU status page (`:80`).

> This web app **replaces the old manual flow** (ssh + setsid + scp). Do **not** hand-run tts/flux/assemble/ltx — the web app orchestrates it.

## 0. Starting-point files (read in this order)
1. `PromptForAgentNew.md` ← this file (master instructions).
2. `README.md` — repo map.
3. `webapp/README.md` — the web service (what it does, how to run).
4. `docs/GPU_SETUP.md` — GPU provisioning (script + exact model list/sizes).
5. `docs/JSON_FORMATS.md` — the two manifest schemas (the web app auto-detects both OLD variants).
6. `docs/RESUME_Aug28.md` + `docs/RESUME_GUIDE_R4.md` — latest connection state + hard-won rules.
7. `docs/ARCHITECTURE.md` — full architecture (LTX-2.3 §F, prompt-split §E).

## 1. Clone the repo
```
git clone https://github.com/bilalk/VidProcessingGPU
cd VidProcessingGPU
git checkout BranchAug29      # (or main once merged)
```

## 2. GPU server — connect + provision (blank AMD MI300X)
- SSH as `root`: `ssh -i <key> root@<GPU_IP>`. ComfyUI API = `http://127.0.0.1:8188` (NEVER `localhost`).
- One-shot install: `bash scripts/setup_new_gpu2.sh` (Python venv, PyTorch ROCm 7.2, ComfyUI systemd service, Noto CJK/Arabic fonts).

> 🔒 **SECURITY (non-negotiable):** ComfyUI MUST bind `127.0.0.1`, NEVER `0.0.0.0`.
> Publicly exposing unauthenticated ComfyUI (`--listen 0.0.0.0`) is exactly how a **Monero
> cryptominer** was injected into this project's GPU box in Aug-2026 (dropped
> `/usr/lib/shared/multipatid` + a one-liner into ~150 `.py` files, which also crash-looped
> ComfyUI). `setup_new_gpu2.sh` uses `127.0.0.1`; if you must expose it, put auth in front of it.
> Expose only SSH (22, key-auth); rotate keys if a box is ever suspected.
- Models into `/root/ComfyUI/models/` (list + sizes in `docs/GPU_SETUP.md`): `ltx-2.3-22b-distilled-fp8`, `gemma_3_12B_it_fp4_mixed`, `flux1-dev`, `t5xxl_fp8`, `clip_l`, `ae`.
- Deploy the pipeline scripts + one-time music bed:
  ```
  scp pipeline/flux/flux_gen_opt.py scripts/tts_29.py scripts/assemble_29.py root@GPU:/root/reels_r3/
  scp scripts/ltx_29.py root@GPU:/root/reels_ltx29/
  scp scripts/status.py root@GPU:/root/status.py
  scp pipeline/flux/gen_bed_r3.py root@GPU:/root/reels_r3/
  ssh root@GPU "cd /root/reels_r3 && /root/ComfyUI/venv/bin/python gen_bed_r3.py"   # creates bed.wav ONCE
  ```
- Start the GPU status page: `ssh root@GPU "setsid /root/ComfyUI/venv/bin/python /root/status.py > /tmp/status.log 2>&1 < /dev/null &"`
  - `status.py` listens on `127.0.0.1:8888`. Expose it on `:80` via Caddy (`reverse_proxy :80 -> 127.0.0.1:8888`), or edit its last line to `S(('0.0.0.0', 80), H).serve_forever()`.
- Verify: `systemctl is-active comfyui` = `active`; `curl -s 127.0.0.1:8188/system_stats` = JSON; status.py answers; `/root/reels_r3/bed.wav` exists.

**Server layout the web app expects** (it pushes its own manifests/scripts, so only these python files + bed.wav are needed):
- `/root/reels_r3/` → `tts_29.py`, `flux_gen_opt.py`, `assemble_29.py`, `gen_bed_r3.py`, `bed.wav`, `img/`, `tts/`.
- `/root/reels_ltx29/` → `ltx_29.py` (it creates its own `clips_m/ clips_d/ out_mobile/ out_desktop/ build/`).
- ⚠️ `ltx_29.py` reads the manifest from the **hardcoded** path `/root/reels_r3/manifest_29aug_all.json` (the web app writes it there) and reuses `/root/reels_r3/img` + `/root/reels_r3/tts`. Do not change these paths.

## 3. Windows client — install the web service
- Prereqs: Git, Python 3.11+, OpenSSH client. Put the GPU SSH private key at `C:\Users\<you>\.ssh\id_newgpu`.
- Deploy the web app to `C:\ReelFactoryWeb`:
  ```
  copy webapp\*  C:\ReelFactoryWeb\
  cd C:\ReelFactoryWeb
  pip install -r requirements.txt          # flask paramiko waitress
  ```
- Install the service — opens firewall **5000** + creates an auto-start scheduled task (**self-restarts on crash**, and `auto_resume()` re-attaches to any job that was mid-run):
  ```
  powershell -ExecutionPolicy Bypass -File install_service.ps1
  ```
- Verify: `http://localhost:5000` loads and `/api/status` returns `"status":"idle"`.
- **After a host reboot** the service auto-starts via the `ReelFactoryWeb` scheduled task. To start it
  manually: `schtasks /run /tn ReelFactoryWeb` (or `powershell -File C:\ReelFactoryWeb\run_service.ps1`).
  Always confirm `curl http://localhost:5000/api/status` before running a batch.

## 4. Drive it from the browser (`http://<client_ip>:5000`)
1. Upload **two JSON manifests** (OLD ~60s schema — see `docs/JSON_FORMATS.md`).
2. Pick **Mode**: `FLUX + LTX` (mobile + desktop) or `FLUX only` (mobile). Set GPU IP + SSH-key path + subtitle burn.
3. Click **Analyze** → validates schema + orientation, **auto-detects** the `29aug` vs `aug28` variant, and reports **redundant topics** against every past JSON (it blocks and lists them, with a "proceed anyway").
4. Click **Start** → the app renumbers to **fresh ids** (continues from the highest id found across past JSONs), pushes the canonical manifest to the server, launches the pipeline detached, polls the logs, and **pulls finished videos to the host**:
   - FLUX → `C:\ProjectComfy\reelsGPU2\flux_29aug\<channel>\<id>.mp4`
   - LTX → `C:\ProjectComfy\reelsGPU2\ltx_29aug_mobile\<channel>\<id>.mp4` + `ltx_29aug_desktop\...`
5. Watch the panel: total / completed / downloaded / current channel / stage / live log. The job runs in a **background thread** — **refreshing/closing the browser is safe** (it only re-fetches `/api/status`).

## 5. GPU status page (`http://<gpu_ip>` / `:80`)
Shows the **same** batch: `BATCH: <json1> + <json2>` · `PHASE: FLUX - … / LTX - channel …` · `done N/24` · `avg … sec/reel` · `ETA ~… min` · GPU temp/power/VRAM · ComfyUI queue · live FLUX/LTX log tail. It has a manual **Refresh** button (fetches `/api` — no auto-timer).

## 6. How client ↔ server ↔ status page communicate
Everything flows through the **server filesystem** (no direct client↔status link):
- **Client** (web app, `:5000`) — over SSH(paramiko)/SFTP — writes `/root/reels_r3/manifest_web_g1.json`, `_g2.json`, `manifest_29aug_all.json`, `web_batch.json` (the JSON names + start id), `web_flux.sh`, and `/root/reels_ltx29/web_ltx.sh`; reads the logs to track progress; SFTP-pulls the results.
- **Pipeline** (server, detached) writes `/root/reels_r3/logs/web_flux.log` + `/root/reels_ltx29/logs/web_ltx.log`.
- **status.py** (server, `:80`) reads `web_batch.json` + those two logs to render the live summary.
→ The GPU page is only up-to-date while `status.py` is running **and** the web app has written `web_batch.json`.

## 7. Hard rules (unchanged)
1. `127.0.0.1:8188`, never `localhost`.
2. No `pkill -f` over SSH — use PIDs.
3. Long work via `setsid … > log 2>&1 < /dev/null &`, then poll the log (the web app's `launch_detached()` does exactly this, and `mkdir -p`s the log dir first).
4. ONE scp/SFTP stream at a time.
5. ComfyUI queue ≤ ~50 jobs → LTX is channel-by-channel; FLUX bursts ≤ ~96.
6. Final mux uses `-c:v libx264`, never `-c:v copy`.
7. Never `apt autoremove` / reinstall packages / redownload models.
8. Renumber every batch to fresh ids (the web app does this automatically).
9. Models: never ask for an HF token. Use `scripts/transfer.sh` (server→server) or the non-gated
   mirrors in `docs/GPU_SETUP.md` — never `huggingface-cli login`/gated repos (`black-forest-labs/FLUX.1-*`,
   Lightricks *LTX-Video*). A 401/`gated` = switch source, not a token.

## 8. Definition of done
- Server: comfyui active, models present, `status.py` serving, `bed.wav` exists.
- Client: service on `:5000` (firewall + auto-start task), `/api/status` = `idle`.
- One end-to-end batch: upload 2 JSONs → Analyze (valid, correct auto-detected format, dedup checked) → Start → FLUX completes → (LTX completes) → all videos pulled to `C:\ProjectComfy\reelsGPU2\{flux_29aug, ltx_29aug_mobile, ltx_29aug_desktop}` → both `:5000` and `:80` show `done 24/24`.
- Write a resume `.md` recording the new GPU IP + ids used (like `docs/RESUME_Aug28.md`).

