#!/bin/bash
cd /root/reels
echo "=== REELS START $(date) ==="
/root/ComfyUI/venv/bin/python tts_gen.py || { echo TTS_STAGE_FAILED; exit 1; }
/root/ComfyUI/venv/bin/python gen_bed.py || { echo BED_FAILED; exit 1; }
python3 flux_gen.py || { echo FLUX_STAGE_FAILED; exit 1; }
python3 assemble.py || { echo ASSEMBLE_STAGE_FAILED; exit 1; }
echo "=== REELS_ALL_DONE $(date) ==="
