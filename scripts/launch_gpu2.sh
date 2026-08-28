#!/bin/bash
# GPU2 Parallel Launch - Runs two 12-reel batches in parallel
# Workspace isolation prevents cross-contamination

PY=/root/ComfyUI/venv/bin/python
SRC=/root/reels_r3

echo "=== GPU BASELINE ==="
/opt/rocm/bin/amd-smi monitor -u 2>/dev/null | head -3
curl -s http://127.0.0.1:8188/system_stats | $PY -c "
import sys,json; d=json.load(sys.stdin)
dev=d.get('devices',[{}])[0]
free=dev.get('vram_free',0); total=dev.get('vram_total',0)
print(f'VRAM: {(total-free)/1e9:.1f}/{total/1e9:.1f}GB')
"

for i in 01 02; do
    WS=/root/reels_g2_w$i
    mkdir -p $WS/{tts,img,build,out,logs}
    cp $SRC/{tts_gen3.py,flux_gen_opt.py,assemble5.py,gen_bed_r3.py} $WS/
    cp $SRC/w$i.json $WS/manifest.json
    for f in tts_gen3.py flux_gen_opt.py assemble5.py; do
        sed -i "s|/root/reels_r3|$WS|g" $WS/$f
    done
    echo "WS w$i ready"
done

# Generate bed for both
cd /root/reels_g2_w01
$PY gen_bed_r3.py 2>/dev/null
cp /root/reels_g2_w01/bed.wav /root/reels_g2_w02/bed.wav 2>/dev/null

# Launch WS1
echo "Launching WS1 (031-042)..."
cd /root/reels_g2_w01
setsid bash -c "$PY tts_gen3.py manifest.json && echo TTS1_DONE && $PY flux_gen_opt.py manifest.json && echo FLUX1_DONE && $PY assemble5.py manifest.json && echo WS1_DONE" > logs/run.log 2>&1 < /dev/null &
echo "WS1 PID=$!"

# Launch WS2
echo "Launching WS2 (043-054)..."
cd /root/reels_g2_w02
setsid bash -c "$PY tts_gen3.py manifest.json && echo TTS2_DONE && $PY flux_gen_opt.py manifest.json && echo FLUX2_DONE && $PY assemble5.py manifest.json && echo WS2_DONE" > logs/run.log 2>&1 < /dev/null &
echo "WS2 PID=$!"

echo "BOTH LAUNCHED"
echo "Monitor: tail -f /root/reels_g2_w01/logs/run.log"

# Sample GPU at peak
sleep 180
echo "=== GPU @ T+180s ==="
/opt/rocm/bin/amd-smi monitor -u 2>/dev/null | head -5
echo "=== WS1 ===" && tail -2 /root/reels_g2_w01/logs/run.log
echo "=== WS2 ===" && tail -2 /root/reels_g2_w02/logs/run.log
