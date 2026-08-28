# 🔄 REEL FACTORY — Aug-28 RESUME / STATE FILE

**Purpose:** a fresh agent can resume from this file alone.
**Last updated:** 2026-08-28 (Aug-27 UTC) — FLUX round COMPLETE, awaiting review before LTX round.

---

## 1. CONNECTION (current)

| Item | Value |
|---|---|
| GPU server IP | `165.245.135.171` (DigitalOcean devcloud, `snapshots-gpu-mi300x1-192gb-devcloud-atl1`) |
| SSH | `ssh -i C:\Users\tester\.ssh\id_newgpu root@165.245.135.171` (BatchMode OK, key is `id_newgpu`) |
| ComfyUI | 0.30.0 on `http://127.0.0.1:8188` (from server; `localhost` is broken — always use `127.0.0.1`) |
| GPU | AMD MI300X, 192 GiB, ROCm 7.2.4, PyTorch 2.13.0 |

> ⚠️ The server IP has changed 5+ times across the project. If SSH fails, ask the owner for the current IP — do NOT re-provision.

## 2. THIS BATCH — WHAT WAS DONE

**Input:** `C:\ProjectComfy\reels\JSON_Aug28_1.json` + `JSON_Aug28_2.json` (12 reels each).

**Renumbering (mandatory — both files reused ids 025-026/seeds 41001-41012):**
- `JSON_Aug28_1` → `manifest_aug28_g1.json` ids `059–070`, seeds `41035–41046`
- `JSON_Aug28_2` → `manifest_aug28_g2.json` ids `071–082`, seeds `41047–41058`
- Scripts: `_scripts/renumber_aug28.py` (local) — run from `C:\ProjectComfy\reels`.

**Data bug FIXED:** the `english-to-arabic/-chinese/-spanish` reels had `src`/`tgt` text flipped (carried the `X-to-english` orientation). English voice was asked to speak Arabic/Chinese → edge-tts crashed.
- Fix: swapped `src↔tgt` for those 3 channels (lines + words) via `_scripts/fix_srctgt.py`. `translit` stays put (it always romanizes the non-Latin text).
- Re-pushed manifests + cleared stale TTS cache, re-ran.

**Prompt-split (documented in `ARCHITECTURE.md` §E):**
- `flux_gen_opt.py` / `flux_gen5.py`: `still_prompt()` strips `LTX motion: …` for clean FLUX stills.
- `run_ltx_v3.py`: `ltx_prompt()` drops `cinematic film still`/`composition` tokens, relabels `LTX motion:` → `Camera motion:`.
- Patcher: `_scripts/patch_prompt_split.py` (already applied on server).

## 3. CURRENT STATE

- ✅ **FLUX round COMPLETE** — 24 reels (mobile 9:16 only), `DUAL RUN COMPLETE`, `ok=12/12` ×2, 0 errors.
- ✅ Pulled to **`C:\ProjectComfy\reelsGPU2\flux_aug28\`** (6 channels × 4 reels, each `.mp4` + `.ass` + `.script.txt`).
- ⏳ **AWAITING OWNER REVIEW** of the FLUX videos (especially `en-ar`/`en-zh`/`en-es` to confirm the src/tgt swap reads correctly).
- ⬜ **NEXT: LTX round** on the same 24 reels → mobile + desktop (true 16:9).

## 4. NEXT STEP — LTX ROUND (after owner approves FLUX)

The updated dual-aspect orchestrator is `/root/reels_ltx/run_ltx_v3.py`, which already has `ltx_prompt()` applied.

- It processes **ONE channel at a time**: `python run_ltx_v3.py <channel>` (LTX is sequential by design — single ComfyUI queue + >50-job wipe risk).
- The 6 channels for this batch: reuse the same `manifest_aug28_g1.json` + `manifest_aug28_g2.json` (they contain all 6 channels across both files).
- FLUX keyframes for 059–082 are already cached in `/root/reels_r3/img/` (96 images) — LTX reuses them as first/last frames.
- Launch pattern (per channel):
  ```
  cd /root/reels_ltx && setsid /root/ComfyUI/venv/bin/python run_ltx_v3.py <channel> > logs/run_v3_<ch>.log 2>&1 < /dev/null &
  ```
- Output: `/root/reels_ltx/out_v3_mobile/` (9:16) + `/root/reels_ltx/out_v3_desktop/` (16:9 true horizontal). `.done` markers per reel.
- LTX model: `ltx-2.3-22b-distilled-fp8.safetensors`, text encoder `gemma_3_12B_it_fp4_mixed.safetensors` (do NOT downgrade to `gemma_2` — that was a prior typo).

## 5. HARD-WON RULES (from prior sessions — still valid)

1. Use `127.0.0.1:8188`, never `localhost`.
2. No `pkill -f` over SSH — use PIDs.
3. Long work via `setsid … > log 2>&1 < /dev/null &`, then poll the log (never block a single ssh call >~25s).
4. ONE scp stream at a time (parallel scp collapses the link / trips sshd MaxStartups).
5. ComfyUI queue ≤ ~50 jobs (soft-restart wipes queue). FLUX bursts 96 fine; LTX is done channel-by-channel.
6. Final mux MUST use `-c:v libx264`, never `-c:v copy` (corrupts h264 on this ffmpeg).
7. Do NOT reinstall packages / rerun `apt` / re-download models.
8. PowerShell piping binary (`ssh | tar`) corrupts data — use scp (or tar-to-file → scp → local extract).

## 6. KEY FILES

| Where | Path |
|---|---|
| Local manifests | `C:\ProjectComfy\reels\manifest_aug28_g1.json`, `manifest_aug28_g2.json` |
| Local review out | `C:\ProjectComfy\reelsGPU2\flux_aug28\` |
| Arch doc + prompt-split | `C:\ProjectComfy\reels\ARCHITECTURE.md` (§E) |
| Server FLUX scripts | `/root/reels_r3/{flux_gen_opt,flux_gen5,tts_gen3,assemble5,run_dual}.py/.sh` |
| Server LTX orchestrator | `/root/reels_ltx/run_ltx_v3.py` |
| Server manifests | `/root/reels_r3/manifest_aug28_g{1,2}.json` |
---

## 7. CYCLE STOPPED — owner closed this batch (2026-08-28)

**Decision:** batch (ids 059–082) considered **DONE**. Pipeline stopped cleanly (orchestrators killed + ComfyUI queue cleared; comfyui.service itself is still up).

**What got generated:**
- FLUX round: all 24 reels (mobile only) → `C:\ProjectComfy\reelsGPU2\flux_aug28\`
- LTX round: **8 reels** fully (mobile + desktop): `ar-en-059/060/071/072`, `zh-en-061/062/073/074` → `C:\ProjectComfy\reelsGPU2\ltx_aug28_mobile\` + `ltx_aug28_desktop\`
- LTX aborted mid-`english-to-arabic` (en-ar-063 in progress) when the stop order came.

**NEXT BATCH numbering:** starts at **100** (IDs `100-xxx` onward). The owner will supply two new JSON files. Reuse the same flow: renumber to fresh IDs → verify src/tgt orientation (`english-to-X` must be src=English) → FLUX round (mobile) → review → LTX round (mobile+desktop).

