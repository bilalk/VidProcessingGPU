# 🔄 REEL FACTORY — MASTER RESUMPTION GUIDE (Session 5+)
## Last updated: 2026-08-04 ~22:00 UTC | Session 5 (post-optimization)

**This is the single source of truth. Read this first after any crash or session restart.**

---

## 1. QUICK CONNECT

| What | Details |
|---|---|
| **GPU Server IP** | `134.199.198.57` |
| **SSH** | `ssh -i C:\Users\faraz\.ssh\id_ed25519 root@134.199.198.57` |
| **RDP** | `134.199.198.57:3389` — user `faraz` / password `Faraz@GPU2026` |
| **ComfyUI** | `http://134.199.198.57:8188` (from browser) or `http://127.0.0.1:8188` (from server) |
| **SSH key** | `C:\Users\faraz\.ssh\id_ed25519` (ED25519, no passphrase) |

---

## 2. SERVER STATE (VERIFIED)

| Item | Status |
|---|---|
| GPU | AMD Instinct MI300X VF, 205.8 GB VRAM |
| ComfyUI | 0.29.0, running as systemd service, auto-start on boot |
| Workspace | `/root/reels_r3/` (active). Old workspaces `/root/reels/` and `/root/reels_dsv/` are untouched |
| Models | flux1-dev (23GB), t5xxl (4.6GB), clip_l (235MB), ae vae (320MB) — all in `/root/ComfyUI/models/` |
| Fonts | 30 CJK, 4 Naskh Arabic (fc-list verified) |
| Tools | edge-tts 7.2.8, ffmpeg 6.1.1, ffprobe, Python 3.12.3 at `/root/ComfyUI/venv/bin/python` |
| RDP | `faraz` / `Faraz@GPU2026`, auto-start + always-restart on boot |
| Disk | ~450 GB free |

---

## 3. FILE STRUCTURE

### On server (`/root/reels_r3/`)
```
flux_gen5.py       Sequential FLUX generator (original, safe)
assemble5.py       4-panel + recap card assembly (original)
flux_gen_opt.py    ⚡ Burst-submit FLUX (all jobs at once)
assemble_opt.py    ⚡ Ultrafast encode + Wan hero panel support
wan_hero_v2.py     ⚡ Wan 2.1 T2V hero clips (fixed: no flicker)
tts_gen3.py        Edge-TTS for R3+ schema
gen_bed_r3.py      Procedural music bed → bed.wav
run_r3.sh          Original orchestrator
run_opt.sh         ⚡ Optimized orchestrator (Wan + burst FLUX + ultrafast)
manifest_*.json    Reel definitions
hero/              Wan hero clips (hero_<id>.mp4)
tts/               Cached TTS mp3s
img/               Cached FLUX PNGs
build/<reel_id>/   Assembly intermediates
out/<channel>/     Final MP4s + ASS + script.txt
logs/              Run logs
```

### Local Windows (`D:\ProjectComfy\reels\`)
```
REEL_FACTORY_RESUME.md              Master state file
PROMPT_FOR_FABLE5_R4.txt            Original prompt for Fable 5
PROMPT_FOR_FABLE5_R4_UPDATED.txt    ⚡ Updated prompt (IP-Adapter + Wan ready)
RESUME_GUIDE_R4.md                  This document
_scripts\round3\                     Round 3 scripts + logs + ALL optimization scripts
_scripts\round4\                     Round 4 manifests (next batch)
_scripts\xrdp-override.conf          RDP persistence config
_scripts\download_ip_adapter.py      IP-Adapter model downloader
_scripts\setup_ip_adapter.py         IP-Adapter setup script
<channel>\                           Per-channel reel storage
```

---

## 4. CURRENT PIPELINE STATUS

| Round | Reels | Status |
|---|---|---|
| R1 (pilot) | 12 | ✅ DONE — delivered |
| R2 (batch) | 120 | ✅ DONE — delivered |
| R3 (recovered) | 12 | ✅ DONE — delivered (re-encoded after `-c:v copy` bug fixed) |
| **R4 (next)** | **60 (planned)** | ⏳ Waiting for Fable 5 manifest |

---

## 5. CRITICAL BUG FIXED (SESSION 5)

**Bug:** `-c:v copy` in final audio mux step corrupts h264 NAL units on this ffmpeg version. Videos show garbage/no video in players.

**Fix:** Changed `-c:v copy` to `-c:v libx264 -preset veryfast -crf 19 -pix_fmt yuv420p` in `assemble5.py` line 163.

**Affected:** All files generated before 2026-08-04 20:30 UTC. All re-encoded and re-pulled.

---

## 6. HOW TO RUN A BATCH (STEP BY STEP)

1. **Prepare manifest:** Place valid `manifest_r4.json` in both `D:\ProjectComfy\reels\_scripts\round4\` and `/root/reels_r3/`
2. **Push and launch:**
   ```
   scp -O -i C:\Users\faraz\.ssh\id_ed25519 manifest.json root@134.199.198.57:/root/reels_r3/
   ssh -i C:\Users\faraz\.ssh\id_ed25519 root@134.199.198.57 "bash -c 'setsid bash /root/reels_r3/run_r3.sh > /root/reels_r3/logs/r4_b01.log 2>&1 < /dev/null &'"
   ```
3. **Monitor:** `ssh ... "tail -20 /root/reels_r3/logs/r4_b01.log"`
4. **Pull (ONE scp at a time):**
   ```
   scp -O -i C:\Users\faraz\.ssh\id_ed25519 root@134.199.198.57:/root/reels_r3/out/<channel>/<reel_id>.mp4 D:\ProjectComfy\reels\<channel>\
   ```
5. **Verify:** Compare MD5 hashes between server and local

---

## 7. PIPELINE RULES (HARD-WON — NEVER BREAK THESE)

1. Use `127.0.0.1:8188` not `localhost` on the server
2. No `pkill -f` over SSH — use PIDs
3. Write remote script files, never inline loops
4. Keep remote calls < 25s — long work via `setsid bash script.sh > log &`
5. ONE scp stream at a time using `scp -O` with full dest filename
6. ComfyUI queue ≤ ~24 jobs — flux_gen5 does sequential single-job (safe)
7. Do NOT kill/restart ComfyUI unless absolutely necessary
8. Do NOT reinstall any packages
9. Isolated workspace: use `/root/reels_r3/`, never touch other workspaces
10. Final mux MUST use `-c:v libx264` not `-c:v copy` (see §5)
11. After any crash: check if leftover `setsid bash` processes are running via `ps aux | grep reels`
12. Check disk before running: `df -h /`

---

## 8. RESUME CHECKLIST

- [ ] SSH works to 134.199.198.57
- [ ] `systemctl is-active comfyui` = active
- [ ] `curl -s --max-time 5 http://127.0.0.1:8188/system_stats` returns JSON
- [ ] `df -h /` shows > 50 GB free
- [ ] `ps aux | grep -E 'run_r3|flux_gen|assemble'` — kill any stale runs
- [ ] Read this file fully
- [ ] Read `REEL_FACTORY_RESUME.md` for last known state
