#!/bin/bash
# FULL SETUP — ComfyUI + models + fonts + pipeline from scratch
# Run on 129.212.180.144 as root
set -e

echo "=== 1. System packages ==="
apt-get update -qq
apt-get install -y --fix-missing \
    xrdp xorgxrdp \
    fonts-noto-core fonts-noto-cjk fonts-noto-naskh-arabic \
    libass-dev libsdl2-dev libgl1 \
    python3-pip python3-venv python3-dev \
    git curl wget \
    ffmpeg \
    2>&1 | tail -3
echo "SYSTEM PACKAGES DONE"

echo "=== 2. RDP setup ==="
echo "faraz:Faraz@GPU2026" | chpasswd 2>/dev/null || echo "faraz account OK"
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
echo "RDP DONE"

echo "=== 3. Clone ComfyUI ==="
if [ ! -d /root/ComfyUI ]; then
    cd /root
    git clone https://github.com/comfyanonymous/ComfyUI.git
fi
PY=/root/ComfyUI/venv/bin/python
if [ ! -d /root/ComfyUI/venv ]; then
    python3 -m venv /root/ComfyUI/venv
fi
$PY -m pip install --upgrade pip setuptools wheel
echo "COMFYUI CLONED"

echo "=== 4. PyTorch ROCm ==="
$PY -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm7.2
echo "PYTORCH DONE"

echo "=== 5. ComfyUI deps ==="
$PY -m pip install -r /root/ComfyUI/requirements.txt 2>&1 | tail -3
echo "COMFYUI DEPS DONE"

echo "=== 6. Pipeline deps ==="
$PY -m pip install numpy edge-tts huggingface_hub 2>&1 | tail -3
echo "PIPELINE DEPS DONE"

echo "=== 7. Create directories ==="
mkdir -p /root/ComfyUI/models/{checkpoints,diffusion_models,text_encoders,vae,ipadapter,upscale_models,clip_vision,controlnet}
mkdir -p /root/ComfyUI/custom_nodes
mkdir -p /root/reels_r3/{tts,img,build,out,logs}
echo "STRUCTURE DONE"

echo "=== 8. ComfyUI service ==="
cat > /etc/systemd/system/comfyui.service << 'SERVEOF'
[Unit]
Description=ComfyUI
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/root/ComfyUI
ExecStartPre=/bin/bash -c 'for i in 1 2 3 4 5 6 7 8 9 10; do [ -e /dev/kfd ] && [ -e /dev/dri/renderD128 ] && exit 0; sleep 6; done; exit 1'
ExecStart=/root/ComfyUI/venv/bin/python main.py --listen 0.0.0.0 --port 8188 --highvram
Restart=on-failure
RestartSec=15
[Install]
WantedBy=multi-user.target
SERVEOF
systemctl daemon-reload
systemctl enable comfyui
echo "SERVICE CREATED"

echo "=== SETUP COMPLETE ==="
echo "Next: copy models from old server via rsync"
