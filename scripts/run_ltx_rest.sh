#!/bin/bash
# run_ltx_rest.sh - sequentially process the remaining 5 Aug-28 LTX channels
cd /root/reels_ltx
PY=/root/ComfyUI/venv/bin/python
MAN=/root/reels_r3/manifest_aug28_all.json
LOGFILE=logs/run_v3_aug28_rest.log

for ch in chinese-to-english english-to-arabic english-to-chinese english-to-spanish spanish-to-english; do
  echo "=== START $ch $(date '+%H:%M:%S') ===" >> "$LOGFILE"
  $PY run_ltx_v3.py "$ch" "$MAN" >> "$LOGFILE" 2>&1
  echo "=== DONE $ch (exit $?) $(date '+%H:%M:%S') ===" >> "$LOGFILE"
done
echo "=== ALL AUG28 REST COMPLETE $(date '+%H:%M:%S') ===" >> "$LOGFILE"
