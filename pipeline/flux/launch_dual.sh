#!/bin/bash
ROOT=/root/reels_r3
LOGDIR="$ROOT/logs"
mkdir -p "$LOGDIR"
M1="manifest_r4_b06_renumbered.json"
M2="manifest_r4_b07_renumbered.json"
cd "$ROOT"
./gpu_monitor.sh "$LOGDIR" > "$LOGDIR/gpu_monitor_launch.log" 2>&1 &
echo "GPU monitor PID: $!" > "$LOGDIR/launcher_pids.txt"
./run_dual.sh "$M1" "$M2" > "$LOGDIR/run_dual.log" 2>&1 &
echo "Run PID: $!" >> "$LOGDIR/launcher_pids.txt"
echo "Launched"
