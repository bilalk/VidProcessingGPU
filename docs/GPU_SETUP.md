# GPU Server Setup — from a blank AMD MI300X droplet

Tested on Ubuntu 24.04 + ROCm 7.2.4 + AMD Instinct MI300X (192 GiB). DigitalOcean "devcloud" droplet.

## 0. Connect
```bash
ssh -i <key> root@<GPU_IP>
```
ComfyUI listens on `http://127.0.0.1:8188` (use `127.0.0.1`, **not** `localhost`).

## 1. One-shot installer
```bash
scp scripts/setup_new_gpu2.sh root@GPU:/root/
ssh root@GPU "bash /root/setup_new_gpu2.sh"
```
This script performs, in order:
1. `python3.12-venv` install + `python3 -m venv /root/ComfyUI/venv`.
2. PyTorch ROCm: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm7.2`.
3. ComfyUI deps: `pip install -r /root/ComfyUI/requirements.txt` + `numpy edge-tts huggingface_hub insightface onnxruntime`.
4. xrdp enable (+ always-restart override).
5. Noto fonts (CJK + Naskh Arabic).
6. ComfyUI model/custom_nodes dirs.
7. `comfyui.service` (systemd) → `main.py --listen 0.0.0.0 --port 8188 --highvram`, `ExecStartPre` waits for `/dev/kfd` + `/dev/dri/renderD128`.

> ComfyUI is cloned to `/root/ComfyUI` beforehand (or the setup assumes it exists). Boot takes ~100 s after `systemctl restart` (ExecStartPre 60 s GPU wait + ComfyUI-Manager registry fetch).

## 2. Models — place these in `/root/ComfyUI/models/`
| File | Dir | Size |
|---|---|---|
| `ltx-2.3-22b-distilled-fp8.safetensors` | `checkpoints/` | ~29.5 GB |
| `gemma_3_12B_it_fp4_mixed.safetensors` | `text_encoders/` | ~9.4 GB |
| `flux1-dev.safetensors` | `checkpoints/` | ~23 GB |
| `t5xxl_fp8_e4m3fn.safetensors` | `text_encoders/` | ~4.9 GB |
| `clip_l.safetensors` | `text_encoders/` | ~235 MB |
| `ae.safetensors` | `vae/` | ~320 MB |

Download from HuggingFace (Lightricks for LTX/FLUX) OR **`scripts/transfer.sh`** copies them server→server (`scp` from `134.199.198.57` or another warm GPU box). Models are **not gated** (LTX-2 22B is openly downloadable; FLUX.1-dev is public).

## 3. Deploy pipeline code
```bash
scp pipeline/flux/*.py pipeline/flux/*.sh root@GPU:/root/reels_r3/
scp pipeline/ltx_v3/*.py root@GPU:/root/reels_ltx/
scp pipeline/v2/*.py        root@GPU:/root/reels_r3/ ; scp pipeline/v2/ltx_v2.py root@GPU:/root/reels_ltx2/
```

## 4. Verify
```bash
ssh root@GPU "systemctl is-active comfyui && curl -s http://127.0.0.1:8188/system_stats"
```
Expect `comfyui` active + a JSON with `devices[0].name = "AMD Instinct MI300X"` and ~205.8 GB VRAM.

## 5. Workspaces on the server
| Path | Contents |
|---|---|
| `/root/reels_r3/` | FLUX + TTS + assemble scripts, manifests, cached `img/` + `tts/`, `bed.wav`, output `out/` |
| `/root/reels_ltx/` | OLD-format LTX (FLF) `run_ltx_v3.py`, output `out_v3_mobile|desktop/` |
| `/root/reels_ltx2/` | NEW-format LTX (I2V) `ltx_v2.py`, output `out_mobile|desktop/` |
| `/root/ComfyUI/` | ComfyUI + venv + models |

## 6. Common gotchas
- `localhost` is broken on this image → always `127.0.0.1`.
- First LTX/FLUX run after boot reloads the model (~30–60 s VRAM alloc) — expect a slow first clip.
- Disk: models ≈ 123 GB; keep > 50 GB free before a run.
- `comfyui.service` uses `--highvram` (whole model in VRAM). GPU idle after queue clear holds ~21% VRAM (model residency).
