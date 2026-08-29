#!/bin/bash
# wait for the running arabic-to-english channel to finish, then run the remaining 5 channels sequentially
while ! grep -q "CHANNEL arabic-to-english COMPLETE" /root/reels_ltx29/run.log 2>/dev/null; do sleep 20; done
PY=/root/ComfyUI/venv/bin/python
for ch in chinese-to-english english-to-arabic english-to-chinese english-to-spanish spanish-to-english; do
  echo "[$(date '+%H:%M:%S')] START $ch" >> /root/reels_ltx29/run_all.log
  $PY /root/reels_ltx29/ltx_29.py "$ch" >> /root/reels_ltx29/run_all.log 2>&1
  echo "[$(date '+%H:%M:%S')] DONE $ch" >> /root/reels_ltx29/run_all.log
done
echo "[$(date '+%H:%M:%S')] ALL_DONE" >> /root/reels_ltx29/run_all.log
