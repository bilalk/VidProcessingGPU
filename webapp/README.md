# Reel Factory — web service (104.211.18.21:5000)

Self-serve web UI for the **OLD ~60s 4-panel pipeline**. Upload two JSON manifests in
the browser, and it validates, dedups, renumbers, runs on the GPU server, and pulls
the finished videos back to the host PC — no tokens / no VS Code.

## Run / install
```powershell
# one-time:
cd C:\ReelFactoryWeb
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File install_service.ps1   # firewall + auto-start task
# (or) run in foreground:
python app.py
```
Then open http://104.211.18.21:5000 (and open port 5000 in the Azure NSG).

## Flow
1. Upload 2 JSONs (OLD format — either **29aug** `term/translation/narration/scene-objects`
   or **aug28** `src/tgt/translit/scene-strings`; auto-detected).
2. Choose mode: **FLUX + LTX** (mobile + desktop, ~60s) or **FLUX ONLY** (mobile).
3. "Analyze" → validates + reports **redundant topics** against every past JSON under
   `C:\ProjectComfy\reels\` + `C:\ProjectComfy\`.
4. "Start" → renumbers to fresh IDs (continues from the highest used id), pushes the
   canonical 29aug manifest to the server, runs the deployed pipeline, pulls results.
5. Results land in `C:\ProjectComfy\reelsGPU2\{flux_29aug, ltx_29aug_mobile, ltx_29aug_desktop}`.

## GPU server
- Default host `129.212.190.223`, key `C:\Users\tester\.ssh\id_newgpu` (editable in the UI).
- Reuses the deployed scripts: `/root/reels_r3/{tts_29,flux_gen_opt,assemble_29}.py` and
  `/root/reels_ltx29/ltx_29.py`.
- **Safety:** the job waits until no pipeline process is running before pushing a new
  batch (never collides with an in-flight run), and never touches ComfyUI / models /
  packages.

## Files
- `app.py` — Flask routes + job orchestration.
- `pipeline.py` — detection / validation / dedup / normalization / renumber (pure logic).
- `gpu.py` — paramiko SSH/SFTP wrapper.
- `templates/index.html` — UI.
- `state/` — config, job status, history. `uploads/` — uploaded manifests.

## Note (subtitle toggle)
The "Handle later" subtitle option is captured in config; v1 still burns subtitles
(server `assemble_29.py` is hardwired to burn). Wiring the no-burn path is a small
server-side patch, left for a follow-up to avoid touching the live scripts.
