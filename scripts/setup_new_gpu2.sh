#!/bin/bash
# FULL SETUP for GPU server 129.212.180.144 — complete from scratch
set -e

echo "=== PHASE 1: Python venv ==="
apt-get install -y python3.12-venv 2>/dev/null || true
if [ ! -d /root/ComfyUI/venv ]; then
    python3 -m venv /root/ComfyUI/venv
fi
PY=/root/ComfyUI/venv/bin/python
$PY -m pip install --upgrade pip setuptools wheel 2>&1 | tail -2
echo "VENV OK"

echo "=== PHASE 2: PyTorch ROCm ==="
$PY -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm7.2 2>&1 | tail -3
echo "TORCH OK"

echo "=== PHASE 3: ComfyUI + pipeline deps ==="
$PY -m pip install -r /root/ComfyUI/requirements.txt 2>&1 | tail -3
$PY -m pip install numpy edge-tts huggingface_hub insightface onnxruntime 2>&1 | tail -3
echo "DEPS OK"

echo "=== PHASE 4: RDP ==="
systemctl enable xrdp xrdp-sesman
systemctl restart xrdp xrdp-sesman
mkdir -p /etc/systemd/system/xrdp.service.d
cat > /etc/systemd/system/xrdp.service.d/override.conf << 'UNITEOF'
[Service]
Restart=always
RestartSec=10
StartLimitIntervalSec=0
[Unit]
After=network.target network-online.target
Wants=network-online.target
UNITEOF
systemctl daemon-reload
echo "RDP OK"

echo "=== PHASE 5: Naskh fonts ==="
mkdir -p /usr/share/fonts/truetype/noto
cd /tmp
wget -q https://github.com/google/fonts/raw/main/ofl/notonaskharabic/NotoNaskhArabic%5Bwght%5D.ttf -O NotoNaskhArabic.ttf 2>/dev/null && cp NotoNaskhArabic.ttf /usr/share/fonts/truetype/noto/ && fc-cache -f 2>/dev/null && echo "NASKH OK" || echo "NASKH will copy from old server"

echo "=== PHASE 6: Model dirs ==="
mkdir -p /root/ComfyUI/models/{checkpoints,diffusion_models,text_encoders,vae,ipadapter,upscale_models,clip_vision,controlnet}
mkdir -p /root/ComfyUI/custom_nodes
mkdir -p /root/reels_r3/{tts,img,build,out,logs}
echo "DIRS OK"

echo "=== PHASE 7: ComfyUI service ==="
cat > /etc/systemd/system/comfyui.service << 'SERVEOF'
[Unit]
Description=ComfyUI
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/root/ComfyUI
ExecStartPre=/bin/bash -c 'for i in $(seq 1 10); do [ -e /dev/kfd ] && [ -e /dev/dri/renderD128 ] && exit 0; sleep 6; done; exit 1'
ExecStart=/root/ComfyUI/venv/bin/python main.py --listen 127.0.0.1 --port 8188 --highvram
Restart=on-failure
RestartSec=15
[Install]
WantedBy=multi-user.target
SERVEOF
systemctl daemon-reload
systemctl enable comfyui
echo "SERVICE OK"

echo "=== SETUP PHASES 1-7 COMPLETE ==="
echo "NEXT: server-to-server model transfer from 134.199.198.57"
