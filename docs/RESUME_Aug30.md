# 🔄 REEL FACTORY — Aug-30 RESUME / STATE FILE

**Purpose:** a fresh agent (or human) can resume from this file alone.
**Last updated:** 2026-08-30 — server provisioned, client ready, MODELS + service install pending.

---

## 1. CONNECTION (current)

| Item | Value |
|---|---|
| GPU server IP | `134.199.196.177` (fresh DigitalOcean devcloud MI300X droplet, hostname `2`) |
| SSH | `ssh -i C:\Users\faraz\.ssh\id_ed25519 root@134.199.196.177` (BatchMode OK) |
| GPU | AMD Instinct MI300X VF, 205.8 GB VRAM, ROCm 7.2, PyTorch 2.13.0 (`torch-2.13.0+rocm7.2`) |
| ComfyUI | 0.34.0 on `http://127.0.0.1:8188` (systemd `comfyui.service`, `--listen 127.0.0.1 --highvram`) |
| GPU status page | `http://134.199.196.177/` (`:80`) — Caddy → `status.py` on `127.0.0.1:8889` |
| Web client | `http://localhost:5000` (Windows), key `C:\Users\faraz\.ssh\id_ed25519` |

> ⚠️ The OLD warm box `134.199.198.57` is **DEAD** (IP rotated). Models must come from HuggingFace (NOT server→server transfer).

---

## 2. WHAT WAS DONE (this session)

### Server (134.199.196.177)
- Cloned ComfyUI → `/root/ComfyUI` (main branch).
- Installed `xrdp` (was missing → `setup_new_gpu2.sh` phase 4 would `set -e`-abort otherwise).
- Ran `setup_new_gpu2.sh` (all 7 phases ✅): python3.12 venv, PyTorch ROCm 7.2, ComfyUI deps
  (+numpy edge-tts huggingface_hub insightface onnxruntime), RDP, Noto Naskh Arabic font, model dirs, `comfyui.service`.
- Started ComfyUI: `systemctl is-active comfyui` = `active`; `/system_stats` shows
  `AMD Instinct MI300X VF`, `vram_total 205822885888` (205.8 GB).
- Deployed pipeline scripts (all `.py`, CRLF stripped on server):
  - `/root/reels_r3/` → `tts_29.py`, `flux_gen_opt.py`, `assemble_29.py`, `gen_bed_r3.py`
  - `/root/reels_ltx29/` → `ltx_29.py`
  - `/root/status.py`
- Generated music bed: `/root/reels_r3/bed.wav` (31.7 MB) via `gen_bed_r3.py`.
- Status page: `status.py` serves on `127.0.0.1:8889` (as a `status.service` systemd unit),
  fronted by Caddy `:80` (`/etc/caddy/Caddyfile` → `:80 { reverse_proxy 127.0.0.1:8889 }`).

### Client (Windows, user `faraz`)
- Cloned repo → `C:\Users\faraz\Desktop\VidProcessingGPU`, checked out `BranchAug29`.
- Deployed webapp → `C:\ReelFactoryWeb` (xcopy), `pip install flask paramiko waitress` done.
- Fixed hardcoded paths:
  - `run_service.ps1` → `$PY = C:\Users\faraz\AppData\Local\Programs\Python\Python312\python.exe`
  - `app.py` `load_config()` defaults → `gpu_host=134.199.196.177`, `gpu_key=C:\Users\faraz\.ssh\id_ed25519`
- Smoke test: `/api/status` → `"status":"idle"`; `/api/config` returns correct host/key.
- Paramiko connectivity verified (host + `bed.wav` + ComfyUI `/system_stats` all reachable).

---

## 3. CURRENT STATE — REMAINING (blocked)

| Step | Status |
|---|---|
| Models into `/root/ComfyUI/models/` | ⛔ **BLOCKED** — gated on HF (needs token + license accept), ~67 GB |
| Windows service install (firewall 5000 + auto-start task) | ⛔ **BLOCKED** — needs **admin elevation** |
| End-to-end batch (upload 2 JSONs → Analyze → Start → pull) | ⏳ blocked on the above two |

### 3a. MODELS (HuggingFace — the old server is dead)

| File | Dir | Size | HF source | Gate |
|---|---|---|---|---|
| `ltx-2.3-22b-distilled-fp8.safetensors` | checkpoints/ | ~29.5 GB | `Lightricks/LTX2` | **gated (401)** |
| `gemma_3_12B_it_fp4_mixed.safetensors` | text_encoders/ | ~9.4 GB | `Lightricks/LTX2` | **gated (401)** |
| `flux1-dev.safetensors` | checkpoints/ | ~23 GB | `black-forest-labs/FLUX.1-dev` | **gated (`gated:auto`)** |
| `ae.safetensors` | vae/ | ~320 MB | `black-forest-labs/FLUX.1-dev` (or -schnell) | gated |
| `t5xxl_fp8_e4m3fn.safetensors` | text_encoders/ | ~4.9 GB | `comfyanonymous/flux_text_encoders` | **public** |
| `clip_l.safetensors` | text_encoders/ | ~235 MB | `comfyanonymous/flux_text_encoders` | **public** |

**To proceed:** log in to HF on the server (`huggingface-cli login` with a token that has
accepted the FLUX.1-dev + Lightricks LTX2 licenses), then download the 6 files into the dirs
above. Only `t5xxl_fp8_e4m3fn` + `clip_l` are download-able without auth.

### 3b. WINDOWS SERVICE (needs admin)

Run as **Administrator**:
```
powershell -ExecutionPolicy Bypass -File C:\ReelFactoryWeb\install_service.ps1
```
This opens firewall TCP 5000 + creates the `ReelFactoryWeb` scheduled task (SYSTEM, at-boot,
self-restart). Then verify `curl http://localhost:5000/api/status` → `"status":"idle"`.

---

## 4. HARD-WON GOTCHAS (new this session)

1. **CRLF breakage:** files copied off a Windows Git checkout carry CRLF. `setup_new_gpu2.sh`
   failed with `bash: line 72: syntax error: unexpected end of file` (heredoc terminator mismatch).
   Fix: `sed -i 's/\r$//' <file>` on the server before running. (Python `.py` files are fine with CRLF.)
2. **`xrdp` not preinstalled** on this droplet → phase 4 of `setup_new_gpu2.sh` (which has `set -e`)
   would abort. Install `xrdp` first.
3. **Caddy + docker already run on this droplet.** Caddy holds `:80`; a pre-existing
   `rocm:latest` docker container (devcloud base image) holds `:8888` (and 8000/30000).
   → `status.py` MUST use a different port; this session uses `127.0.0.1:8889`, Caddy fronts `:80`.
   Do NOT remove the rocm container.
4. **`pgrep -f '...status.py'` self-matches** your own ssh shell (kills the session). Always use
   the `[.]` escape: `pgrep -f 'python /root/status[.]py'`.
5. Windows inline `powershell -Command "..."` with nested quotes echoes instead of runs — use
   `.bat`/`.ps1` files or single-line substring edits.

---

## 5. NEXT STEPS (for the next session)

1. (user provides HF token) `huggingface-cli login` on server → download 6 models (§3a) → restart
   ComfyUI (`systemctl restart comfyui`), confirm `/object_info` lists all checkpoints/text encoders/VAE.
2. (admin) run `install_service.ps1` → confirm `:5000` + scheduled task + idle status.
3. Upload `manifests/old/JSON_Aug28_1.json` + `JSON_Aug28_2.json` for the first end-to-end batch.
4. Verify: both `:5000` (client) and `:80` (GPU) show `done N/N`; videos land in
   `C:\ProjectComfy\reelsGPU2\{flux_29aug, ltx_29aug_mobile, ltx_29aug_desktop}`.
5. Update this file's §3 to mark models + service done.

### Key server commands
```
ssh -i C:\Users\faraz\.ssh\id_ed25519 root@134.199.196.177
systemctl status comfyui status          # both should be active
curl -s http://127.0.0.1:8188/system_stats | head -c 200
curl -s http://127.0.0.1/  # status page via caddy
```
