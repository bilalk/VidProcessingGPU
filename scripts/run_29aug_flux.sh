#!/bin/bash
cd /root/reels_r3
PY=/root/ComfyUI/venv/bin/python
$PY tts_29.py manifest_29aug_g1.json > logs/tts29_g1.log 2>&1 &
$PY tts_29.py manifest_29aug_g2.json > logs/tts29_g2.log 2>&1 &
wait
echo "[$(date '+%H:%M:%S')] TTS_DONE"
$PY flux_gen_opt.py manifest_29aug_g1.json > logs/flux29_g1.log 2>&1 &
$PY flux_gen_opt.py manifest_29aug_g2.json > logs/flux29_g2.log 2>&1 &
wait
echo "[$(date '+%H:%M:%S')] FLUX_DONE"
$PY assemble_29.py manifest_29aug_g1.json >> logs/run_29aug.log 2>&1
$PY assemble_29.py manifest_29aug_g2.json >> logs/run_29aug.log 2>&1
echo "[$(date '+%H:%M:%S')] ALL_DONE"
