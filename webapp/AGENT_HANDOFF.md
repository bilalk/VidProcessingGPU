# AGENT_HANDOFF.md — Reel Factory (single file to give ANY future agent)

## 0. What this is
A self-serve reel factory: two uploaded JSON manifests (24 reels, 6 language channels)
are validated → normalized → renumbered on the host, then rendered on a remote AMD
MI300X GPU (FLUX stills + edge-tts + assemble → FLUX round; then per-channel LTX video
round) and pulled back to this PC.

```
Browser → http://localhost:5000 (Flask/waitress, C:\ReelFactoryWeb)
        → SSH root@134.199.207.148 (key C:\Users\faraz\.ssh\id_ed25519)
            ├─ /root/reels_r3/   FLUX round: tts_29.py → flux_gen_opt.py → assemble_29.py
            │                    out: img/ tts/ out_29aug/ logs/web_flux.log
            ├─ /root/reels_ltx29/ LTX round: ltx_29.py <channel>   logs/web_ltx.log
            ├─ ComfyUI     127.0.0.1:8188 (server-local only)
            └─ status page 127.0.0.1:8889 (server-local only)
Outputs land in C:\ProjectComfy\reelsGPU2\{flux_29aug, ltx_29aug_mobile, ltx_29aug_desktop}
```

## 1. Dashboards
- Host UI + API: http://localhost:5000 and http://localhost:5000/api/status (JSON).
- GPU status page: bound to server-localhost 8889, NOT exposed externally. To view:
  `ssh -i C:\Users\faraz\.ssh\id_ed25519 -L 8889:127.0.0.1:8889 root@134.199.207.148`
  then open http://localhost:8889
- Current batch marker on server: /root/reels_r3/web_batch.json (files + start_id).

## 2. THE JSON LAW (violate = missed reels; proven 2026-09-05 crash)
Feed only the **29aug format** (see docs/REEL_FORMAT_STANDARD.md + docs/REEL_TEMPLATE_29aug.json):
- `words[].term` = FOREIGN word, `words[].translation` = ENGLISH — in ALL 6 channels,
  including english-to-*. The channel name NEVER flips direction.
- `lines[]` = 3 plain ASCII-English strings. `scenes[]` = 4 objects
  (scene_index, shot_type, ltx_motion_profile, prompt; never put "LTX motion:" inside prompt).
- 3 words / 3 lines / 4 scenes per reel; 12 reels per file; 2 files per job; fixed voice
  table per channel (copy from the template). English voice speaking non-Latin text
  (e.g. Chinese) = 0-byte mp3 = assemble crash = whole 12-reel group lost.
- ALWAYS pre-flight: `python C:\Users\faraz\Desktop\verify_new_batches.py`
  (edit FILES list) — must print `FATAL=0 WARN=0`, validate PASS, dedup NONE.

## 3. (a) START A CLEAN RUN
1. Verify the two JSONs (command above). 2. UI: upload file A + file B → Analyze
   (expect 0 issues, no redundant topics) → Start. 3. Watch /api/status:
   flux_running → pulling flux → ltx_running (per channel) → done.
   IDs auto-continue from the max id in the server caches (img/ + tts/) — never reuse.

## 4. (b) CHECK / COMPLETE AN IN-PROGRESS RUN
- `curl http://localhost:5000/api/status` → status, current_channel, log_tail, eta_min.
- App restarts auto-attach to the running server job (`auto_resume()` in app.py) —
  just restart the service and it picks the run back up; downloads resume idempotently
  (existing files are skipped).
- Server truth: `tail /root/reels_r3/logs/web_flux.log` (FLUX) and
  `/root/reels_ltx29/logs/web_ltx.log` (LTX, lines: START/DONE <channel>, CLIP … done=N/24).
- Count health: per reel expect 4 PNGs in img/, 9 mp3s in tts/ (3 L + 3 w + 3 t, all >0
  bytes), 1 mp4 in out_29aug/<channel>/, later 2 mp4s in out_mobile/out_desktop.
  Zero-byte scan: `find /root/reels_r3/tts -size 0` must print nothing.

## 5. Terminate safely (fixed 2026-09-06)
UI "End" → gpu.py kill_pipeline(): kills orchestrators+workers, WAITS for death,
interrupts the running ComfyUI render, clears pending queue and verifies it is empty.
(Old version cleared the queue 1s after pkill and never interrupted the running render
→ ghost clips survived and blocked the next batch.)

## 6. DO-NOT-DELETE (server)
/root/reels_r3/{img,tts,out_29aug} and /root/reels_ltx29/* caches — server_used_ids()
derives the next start id from them; deleting them causes id COLLISIONS on later runs.
Safe to delete: /root/ComfyUI/output strays from dead runs (ids below current batch).

## 7. Known quirks
- GPU status page "PHASE" line reads the newest log file; between rounds it can show a
  stale label from the previous run — trust the FLUX/LTX lines under it.
- Host UI `reels_done` only advances during the LTX round (stays 0 during FLUX) — normal.
- Host PC clock = server UTC + 5h in logs.
