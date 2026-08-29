#!/bin/bash
# SETUP NEW GPU SERVER (129.212.180.144) - Phase 1: System dependencies
# Run as root on new server

set -e

echo "=== PHASE 1: System packages ==="
apt-get update -qq
apt-get install -y --fix-missing xrdp xorgxrdp fonts-noto-core fonts-noto-cjk fonts-noto-naskh-arabic libass-dev python3-pip python3-venv git curl wget 2>&1 | tail -5

echo "=== PHASE 2: Create venv ==="
if [ ! -d /root/ComfyUI/venv ]; then
    python3 -m venv /root/ComfyUI/venv
fi
PY=/root/ComfyUI/venv/bin/python
$PY -m pip install --upgrade pip 2>&1 | tail -2

echo "=== PHASE 3: Python packages ==="
$PY -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm7.2 2>&1 | tail -3
$PY -m pip install numpy edge-tts huggingface_hub insightface onnxruntime opencv-python 2>&1 | tail -3

echo "=== PHASE 4: Verify ==="
echo "Python: $($PY --version)"
echo "PyTorch: $($PY -c 'import torch; print(torch.__version__)')"
echo "ROCm: $($PY -c 'import torch; print(torch.cuda.is_available())')"
echo "FFmpeg: $(ffmpeg -version | head -1 | cut -d' ' -f3)"

echo "=== PHASE 5: Enable RDP ==="
systemctl enable xrdp xrdp-sesman
systemctl restart xrdp xrdp-sesman

echo "SETUP PHASE 1-5 COMPLETE"
