#!/bin/bash
# gpu_monitor.sh - log GPU utilization every 5 seconds
LOGDIR="$1"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/gpu_util.log"
> "$LOG"
START=$(date +%s)
echo "timestamp,elapsed_sec,gpu_util_pct,mem_util_pct,temp_c,power_w" > "$LOG"
while true; do
  # Try amd-smi first, then rocm-smi
  if command -v amd-smi &> /dev/null; then
    OUT=$(amd-smi metric --compute-memory --json 2>/dev/null | head -c 1000)
    if [[ -n "$OUT" ]]; then
      # Parse JSON for first GPU
      GPU_UTIL=$(echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['compute_partition'][0].get('gpu_use', 'NA'))" 2>/dev/null || echo "NA")
      MEM_UTIL=$(echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['compute_partition'][0].get('mem_use', 'NA'))" 2>/dev/null || echo "NA")
      TEMP=$(echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0].get('temperature', 'NA'))" 2>/dev/null || echo "NA")
      POWER=$(echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0].get('power', 'NA'))" 2>/dev/null || echo "NA")
      echo "$(date '+%H:%M:%S'),$(( $(date +%s) - START )),$GPU_UTIL,$MEM_UTIL,$TEMP,$POWER" >> "$LOG"
      sleep 5
      continue
    fi
  fi
  # Fallback to rocm-smi basic
  rocm-smi --showuse --showmeminfo vram --showtemp --showpower 2>/dev/null | tail -n +4 >> "$LOG"
  sleep 5
done
