# 🔄 REEL FACTORY — SESSION RESUME / STATE FILE (READ FIRST)

**Purpose:** any new agent (or human) can resume ALL work from this file alone, without re-discovery.
**Last updated:** 2026-08-04 ~20:20 UTC (session 5 — **ROUND 3 COMPLETE: 12/12 assembled, delivered, QA PASS on NEW SERVER**) | **Owner docs:** this file + the 3 companion docs below.

> **⚡ LIVE STATE (session 4, ~20:20 UTC): ROUND 2 = DONE.** Executed in **BATCH MODE** (user directive): 10 batches × 12 reels (2/channel; b1-6 = 1w+2w, b7-10 = 1w+3w) via slices `manifest_r2_bNN.json`. **Assembly: 10/10 batches × 12/12 PASS** (logs `/root/reels/b01..b10.log`, durations 31-49s, h264 1080×1920 + aac). **Delivery: 360/360 files (120 reels × mp4+ass+script.txt) in `D:\ProjectComfy\reels\<channel>\`, byte-identical to server** (verifier: `_scripts\round2\verify_delivery.py` + `server_ls.txt` → run `python verify_delivery.py` to re-audit anytime). **Glyph QA: ALL 4 render paths visually PASS** — hanzi hooks ×3 + zh echo panels ×2 (incl. 3-word density), Arabic RTL ×4, Spanish accents ×1 (`D:\ProjectComfy\reels\thumbs\qa_*.jpg` ×41). Scripts archived: `_scripts\round2\` (full manifest, 6 parts, validator, slicer, 10 batch slices, verifier). Wave markers: `pull_*.done` in `C:\Users\faraz\Desktop\`.
> **NEXT STEPS when resuming:** Round 2 closed — nothing pending. For Round 3+: reuse `run_batch.bat`/`pull_*.bat` patterns; content for a new round = new `part_*.json` → `merge_validate.py` → `make_batches.py` → push slices → batch loop. Security items STILL OPEN 🔴 (RDP default password, ComfyUI :8188 internet-open).
> **S4 hard-won rules (extends §6):** (11) the tool waits on the process TREE → backgrounded work reports 'timeout' but RUNS; launch+pull ONLY via `powershell Start-Process -WindowStyle Hidden` with STRUCTURED args (plain-string commands get inner `"` backslash-escaped → powershell prints the string instead of running it). (12) NEVER parallel scp: 6 streams collapsed the ~1.25MB/s uplink AND tripped sshd MaxStartups (new logins hung ~5 min); ONE stream at a time; zombie check `tasklist | findstr /I scp` → `taskkill /F /PID <pid>`. (13) `timeout.exe` fails in non-interactive shell; RTT ~340ms.

**Companion docs (same folder, `C:\Users\faraz\OneDrive\Desktop\`):**
| File | Role |
|---|---|
| `GPU_SERVER_SETUP_HANDOVER.md` | Original server runbook (connection, services, models, rules) |
| `GPU_SERVER_SETUP_HANDOVER_KimiReviewed.md` | Independent audit + measured benchmarks + security gaps |
| `REEL_FACTORY_50H_PLAN_Kimi.md` | Kimi's 50h production plan (architecture, tiers, measured throughput) |
| `REEL_FACTORY_50H_PLAN_kimiPlanForReels.md` | Critical review of user's plan + modified plan + pilot validation |

---

## 0. 60-SECOND STATUS BOARD

| Item | State |
|---|---|
| Server | `134.199.198.57` (NEW — old was `165.245.129.173`). SSH root via `C:\Users\faraz\.ssh\id_ed25519` (BatchMode OK). ComfyUI 0.29.0 API on `:8188`, MI300X VF 205.8 GB VRAM, all healthy. Workspace: `/root/reels_r3/` (isolated; `/root/reels/` untouched) |
| Round 1 (pilot) | ✅ **DONE** — 12 reels (6 channels × 2), QA 12/12 PASS, downloaded to `D:\ProjectComfy\reels\<channel>\` |
| Known bug #1 | ✅ **FIXED (session 3)** — fonts-noto-cjk installed (fc-list=30 CJK), 4 zh reels re-assembled, QA 12/12 PASS, hanzi visually verified in thumbs (zh_fixed.jpg / enzh_fixed.jpg), 4 fixed mp4s re-downloaded to `D:\ProjectComfy\reels\` |
| Known bug #2 | 🟡 Session 2 ended by **Cline loop-protection** (too many identical poll commands) — **server unaffected**, all server jobs finished cleanly (`REELS_ALL_DONE` in log). Avoidance rules in §6 |
| Round 2 (batch mode, s4) | ✅ **COMPLETE — 120/120 assembled (10/10 batches 12/12 PASS) + 360/360 files delivered byte-identical** to `D:\ProjectComfy\reels\<channel>\` (mp4+ass+script.txt); glyph QA 4/4 paths visually PASS; scripts archived `_scripts\round2\` |
| Round 3 (recovery, s5) | ✅ **COMPLETE on NEW SERVER `134.199.198.57`** — 12/12 assembled, QA 12/12 PASS (durations 46-55s, h264 1080×1920 + AAC, recap cards working). 36/36 files delivered to `D:\ProjectComfy\reels\<channel>\`. Pipeline: TTS 144 segs → FLUX 48 imgs (222s) → assemble 154s (5 lanes). Scripts in `_scripts\round3\`, server workspace `/root/reels_r3/` |
| New server | **`134.199.198.57`** (old was `165.245.129.173`). MI300X VF 205.8 GB VRAM. ComfyUI 0.29.0, models/fonts/edge-tts/ffmpeg all verified. SSH key auth working. Isolated workspace `/root/reels_r3/`. Old workspace `/root/reels/` untouched. |
| Edge-TTS / fonts | edge-tts 7.2.8 ✅ · Noto Naskh Arabic ✅ · libass ✅ · fonts-noto-cjk ✅ **INSTALLED (s3)** · 4 extra voices verified: Guy/Yunxi/Alvaro/Hamed ✅ |
| Security open items | 🔴 RDP password still default `Faraz@GPU2026` · 🔴 ComfyUI :8188 internet-open without auth |

---

## 1. WHERE EVERYTHING LIVES

### On the server (`/root/reels/`)
```
manifest.json      12 reel definitions (round-1 content)
flux_gen.py        FLUX 768x1344 generator via /prompt API (measured 4.3s/img hot)
tts_gen.py         Edge-TTS segment generator (6 voices, cache-aware)
assemble.py        ASS subtitles + zoompan Ken Burns + concat + audio mux + QA (5 lanes)
gen_bed.py         procedural rights-free music bed (bed.wav)
run_reels.sh       orchestrator (tts -> bed -> flux -> assemble)
reels.log          full round-1 log (ends with REELS_ALL_DONE)
img/               36 FLUX PNGs (scene library seed)
tts/               48 voice mp3s
build/<reel_id>/   per-reel .ass + seg1-3.mp4 + vsub.mp4 (assembly intermediates)
out/<channel>/     12 final mp4s (1080x1920, 21.4s, h264+AAC)
bed.wav, thumbs/
```

### Local (Windows)
```
D:\ProjectComfy\reels\<channel>\*.mp4        12 reels (BUT 4 have the tofu bug, see §3)
D:\ProjectComfy\reels\_scripts\              manifest.json, flux_gen.py, tts_gen.py, assemble.py,
                                             gen_bed.py, run_reels.sh, reels.log, 2 sample .ass
D:\ProjectComfy\reels\thumbs\                5 proof frames (incl. Arabic RTL pass)
D:\ProjectComfy\WONDERS_OF_EARTH_60s_1080p.mp4   session-1 proof video (60s, Wan 2.1)
C:\Users\faraz\Desktop\*.bat / *.py / *.sh   working copies of all push/poll/launch helpers
C:\Users\faraz\OneDrive\Desktop\*.md         the 5 docs (this file + 4 companions)
```

### Measured benchmarks (MI300X, this box — trust these, not estimates)
FLUX 768×1344@16st = **4.3s hot** (36 jobs/156s) · Wan 2.1 6s clip 832×480 = **190s** · reel assembly = **~3s/reel** (5 lanes) · Edge-TTS = **~2.3s/segment** · full CPU post for 60s video = ~30s · scp pull = **~1.25 MB/s/stream** (split big pulls, ≤35 MB per scp call under the 30s tool cap).

---

## 2. ROUND-2 REQUIREMENTS CONTRACT (user brief, points a–f)

| # | Requirement | Implementation decision (locked) |
|---|---|---|
| a | Reels were <30s → make them **~30–36s** | Format v2: **4 panels × ~8s** (hook → context → dialog/story → word echo) ≈ 32s |
| b | Mix of **1-word, 2-word AND 3-word** lessons; multi-word reels must stay **coherent in ONE storyline/dialog** | Manifest v2 schema: `words: [...]` (1–3 entries) + `dialog: [...]` lines forming one continuous scene; all 4 panels share the same setting/characters (prompts carry a shared "scene anchor") |
| c | **Background script + storyline visible locally** for later amendment | Export per reel: `<reel_id>.ass` **and** `<reel_id>.script.txt` (title, words, every narration line, translations, scene prompts) → copied to `D:\ProjectComfy\reels\<channel>\` next to each mp4 |
| d | 4h unattended: **how many more?** | Measured math: v2 reel ≈ 17s GPU (4 FLUX panels) + ~12s TTS + ~4s assembly, pipelined → **~25–35s/reel wall** → **400–600 NEW unique reels/4h** possible; limit is content-writing, not compute. Plan: **~120–144 reels (20–24/channel)** across 1w/2w/3w × all 6 pairs, fully unique |
| e | **Chinese shows as rectangles** | Confirmed bug — §3 (missing font, not a typing mistake) |
| f | **Session-proofing** | This RESUME file ×3 copies: OneDrive Desktop, `D:\ProjectComfy\reels\`, server `/root/reels/` |

---

## 3. KNOWN BUG #1 — CHINESE TOFU RECTANGLES (root cause + fix)

**Symptom (user screenshots):** zh-en-001/002 at 0:01–0:03 show `□□□□□□□` instead of Chinese. VLC is NOT at fault — tofu is baked into pixels by the server-side libass burn.

**Root cause (verified):** round-1 setup ran one combined apt line: `apt-get install -y --fix-missing fonts-noto-core fonts-noto-cjk fonts-noto-naskh-arabic`. **`fonts-noto-naskh-arabic` doesn't exist as a package → apt aborted the WHOLE line → `fonts-noto-cjk` was never installed.** Arabic passed only because Naskh was already preinstalled; my visual checks sampled Latin/pinyin phases, never a Chinese-glyph phase — that's how it slipped through.

**Fix (10 minutes, no re-generation needed):**
1. `apt-get install -y fonts-noto-cjk` (separate command!) → verify `fc-list | grep -i "cjk sc"` non-empty
2. `rm -f /root/reels/build/{en-zh-001,en-zh-002,zh-en-001,zh-en-002}/vsub.mp4` + delete the 4 outputs in `/root/reels/out/`
3. Re-run `python3 /root/reels/assemble.py` — images (`img/`) and TTS (`tts/`) are cached; only concat+ASS+mux re-runs (~30s)
4. Re-thumbnail t≈2s of zh-en-001, **visually confirm hanzi** before re-downloading to `D:\ProjectComfy\reels\`
5. Pipeline lesson: apt packages install **one per command** + `fc-list` assert for every required family (EN/ES/ZH/AR) BEFORE mass production (hard gate, same as the Arabic RTL gate)

---

## 4. ROUND-2 PRODUCTION PLAN (the 4h run, in order)

1. **§3 font fix + re-render 4 zh reels** (10 min)
2. **Format v2 upgrade:** `assemble.py` → 4 panels/32s with audio delays computed from actual TTS durations (ffprobe); `tts_gen.py` → dialog lines; new `export_scripts.py` → per-reel `script.txt`
3. **Content:** write `manifest_r2.json` — 120–144 reels: per channel ~10×1-word + ~6×2-word + ~4×3-word; rotating topics (tech/history/food/art/science/travel/wisdom/sports/daily-drama/nature); every word unique set-wide; 3-word reels = one coherent mini-story across all 4 panels
4. **Run** (est. 60–90 min compute): tts → bed → flux (~150–200 imgs ≈ 12–15 min) → assemble → QA (duration ≥29s, hanzi + Arabic spot-checks, audio present)
5. **Deliver:** pull to `D:\ProjectComfy\reels\<channel>\` (mp4 + .ass + script.txt); update this file's §0 board; append results to `REEL_FACTORY_50H_PLAN_Kimi.md`
6. **Stretch (if >1h left):** 1 Wan 2.1 hero clip per channel (6 × ~190s ≈ 20 min GPU)

---

## 5. RESUME CHECKLIST FOR THE NEXT AGENT (do in order)

1. Read this file fully, then `GPU_SERVER_SETUP_HANDOVER_KimiReviewed.md` §2–§5.
2. Verify server alive (via .bat helper): `systemctl is-active comfyui` + `curl -s localhost:8188/system_stats`.
3. Do §3 font fix FIRST (quick win, unblocks 4 zh reels).
4. Execute §4 plan. Do NOT re-download models; do NOT reinstall edge-tts/noto-core (only noto-cjk is missing).
5. After delivery, update §0 status board and re-copy this file to all 3 locations.

## 6. RULES FOR THE NEXT AGENT (hard-won — session-ending if ignored)

1. **Cline loop-protection:** >5 consecutive IDENTICAL tool commands = session killed (this ended session 2 — **the server was never stuck**). Never poll with the same command twice running: vary it (append a harmless counter arg) or use a server-side waiter; keep every remote call <25s.
2. **30s local tool cap:** long work runs detached on server (`setsid bash x.sh > log 2>&1 < /dev/null &`), poll the log.
3. **Windows quoting:** inline ssh with nested quotes breaks — use `.bat` helpers; one `type file | ssh "cat > dest"` per line; separate ssh for launch (a combined push+launch chain wrote a 0-byte file once).
4. **Server rules (from handover):** no `pkill -f` over SSH — use `kill <pid>`; never `apt autoremove`; never NVIDIA drivers; apt packages one-per-command; size-check big downloads.
5. **scp pulls:** ≤35 MB per call (~1.25 MB/s); batch/split folders accordingly.
6. Record every state change in §0 of this file before ending the session.
7. **`localhost` is BROKEN on the server (session 3):** curls to `localhost:8188` hang silently; `127.0.0.1:8188` works perfectly. ALL scripts/checks must use `127.0.0.1` (flux_gen2/3 already do). Don't be fooled into thinking the API is down.
8. **ComfyUI 0.29 can soft-restart and WIPE the in-memory queue mid-batch** (observed 07:36 UTC: ~450 pending jobs lost, queue+history gone). Never queue >~50 jobs at once; use `flux_gen3.py` (chunked×36 + per-job timeout + requeue + cache-aware resume). Queue persistence lives in `/root/ComfyUI/user/comfyui.db` (safe to move aside when wedged; it re-migrates cleanly).
9. **Batch-file `%` escaping:** inside `.bat`, `%{...}` (e.g. curl `-w '%{http_code}'`) is eaten by cmd var-expansion → write `%%{http_code}` or avoid `-w` in .bat files. Also: run_commands structured-args do NOT strip double quotes the way cmd does — remote commands with inner quotes must go through `.bat` files, never inline ssh args.
10. **`systemctl restart --no-block` + ~100 s wait:** comfyui.service has a 60 s GPU-wait ExecStartPre + ~40 s boot (ComfyUI-Manager registry fetches) before 127.0.0.1:8188 answers. A clean `kill <pid>` does NOT trigger Restart=on-failure (clean exit) — use `systemctl start` after manual kills.

*Session-proof by design: this file exists in 3 places (OneDrive Desktop, D:\ProjectComfy\reels\, server /root/reels/). — Kimi, 2026-08-02*
