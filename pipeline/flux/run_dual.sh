#!/bin/bash
# run_dual.sh - run two manifests in parallel, then assemble serially
set -e
ROOT=/root/reels_r3
PY=/root/ComfyUI/venv/bin/python
M1="$1"
M2="$2"
LOGDIR="$ROOT/logs"
mkdir -p "$LOGDIR"

M1_NAME=$(basename "$M1" .json)
M2_NAME=$(basename "$M2" .json)

echo "[$(date '+%H:%M:%S')] DUAL RUN START: $M1 + $M2"

# Phase 1: parallel FLUX + TTS generation
echo "[$(date '+%H:%M:%S')] Phase 1: parallel FLUX + TTS generation"

(
  cd "$ROOT"
  $PY flux_gen_opt.py "$M1" > "$LOGDIR/${M1_NAME}_flux.log" 2>&1
  echo "[$(date '+%H:%M:%S')] FLUX done for $M1"
) &
PID_FLUX1=$!

(
  cd "$ROOT"
  $PY flux_gen_opt.py "$M2" > "$LOGDIR/${M2_NAME}_flux.log" 2>&1
  echo "[$(date '+%H:%M:%S')] FLUX done for $M2"
) &
PID_FLUX2=$!

(
  cd "$ROOT"
  $PY tts_gen3.py "$M1" > "$LOGDIR/${M1_NAME}_tts.log" 2>&1
  echo "[$(date '+%H:%M:%S')] TTS done for $M1"
) &
PID_TTS1=$!

(
  cd "$ROOT"
  $PY tts_gen3.py "$M2" > "$LOGDIR/${M2_NAME}_tts.log" 2>&1
  echo "[$(date '+%H:%M:%S')] TTS done for $M2"
) &
PID_TTS2=$!

# Wait for all generation to finish
wait $PID_FLUX1 $PID_FLUX2 $PID_TTS1 $PID_TTS2
echo "[$(date '+%H:%M:%S')] Phase 1 complete."

# Phase 2: music bed (once)
echo "[$(date '+%H:%M:%S')] Phase 2: music bed"
(
  cd "$ROOT"
  $PY gen_bed_r3.py > "$LOGDIR/bed.log" 2>&1
)
echo "[$(date '+%H:%M:%S')] Bed done."

# Phase 3: serial assembly with ffmpeg
echo "[$(date '+%H:%M:%S')] Phase 3: serial assembly with ffmpeg"
(
  cd "$ROOT"
  $PY assemble5.py "$M1" > "$LOGDIR/${M1_NAME}_assemble.log" 2>&1
  echo "[$(date '+%H:%M:%S')] Assembly done for $M1"
)

(
  cd "$ROOT"
  $PY assemble5.py "$M2" > "$LOGDIR/${M2_NAME}_assemble.log" 2>&1
  echo "[$(date '+%H:%M:%S')] Assembly done for $M2"
)

echo "[$(date '+%H:%M:%S')] DUAL RUN COMPLETE"
