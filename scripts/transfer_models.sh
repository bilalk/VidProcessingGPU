#!/bin/bash
# Run on NEW server (129.212.180.144)
# Transfers all ComfyUI models + fonts + pipeline from OLD server (134.199.198.57)
# via server-to-server SSH using key at /root/.ssh/id_ed25519_old

OLD="root@134.199.198.57"
KEY="/root/.ssh/id_ed25519_old"

echo "=== Testing connection to old server ==="
ssh -i $KEY -o StrictHostKeyChecking=no $OLD "echo OK" || exit 1

echo "=== Transferring FLUX models (~23GB) ==="
scp -i $KEY -O $OLD:/root/ComfyUI/models/checkpoints/flux1-dev.safetensors /root/ComfyUI/models/checkpoints/ 2>&1 | tail -3
scp -i $KEY -O $OLD:/root/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors /root/ComfyUI/models/checkpoints/ 2>&1 | tail -3

echo "=== Transferring text encoders (~12GB) ==="
scp -i $KEY -O $OLD:/root/ComfyUI/models/text_encoders/t5xxl_fp8_e4m3fn.safetensors /root/ComfyUI/models/text_encoders/
scp -i $KEY -O $OLD:/root/ComfyUI/models/text_encoders/clip_l.safetensors /root/ComfyUI/models/text_encoders/

echo "=== Transferring VAE ==="
scp -i $KEY -O $OLD:/root/ComfyUI/models/vae/ae.safetensors /root/ComfyUI/models/vae/

echo "=== Transferring Wan models (~46GB) ==="
scp -i $KEY -O $OLD:/root/ComfyUI/models/diffusion_models/wan2.1_t2v_14B_fp8_scaled.safetensors /root/ComfyUI/models/diffusion_models/ &
scp -i $KEY -O $OLD:/root/ComfyUI/models/diffusion_models/wan2.1_i2v_480p_14B_fp8_scaled.safetensors /root/ComfyUI/models/diffusion_models/ &
scp -i $KEY -O $OLD:/root/ComfyUI/models/diffusion_models/wan2.1_i2v_720p_14B_fp8_scaled.safetensors /root/ComfyUI/models/diffusion_models/ &
scp -i $KEY -O $OLD:/root/ComfyUI/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors /root/ComfyUI/models/text_encoders/ &
scp -i $KEY -O $OLD:/root/ComfyUI/models/vae/wan_2.1_vae.safetensors /root/ComfyUI/models/vae/ &
wait

echo "=== Transferring IP-Adapter models ==="
scp -i $KEY -O $OLD:/root/ComfyUI/models/ipadapter/flux-ip-adapter.safetensors /root/ComfyUI/models/ipadapter/
scp -i $KEY -O $OLD:/root/ComfyUI/models/ipadapter/model.safetensors /root/ComfyUI/models/ipadapter/

echo "=== Transferring upscalers ==="
scp -i $KEY -O $OLD:/root/ComfyUI/models/upscale_models/4x-UltraSharp.pth /root/ComfyUI/models/upscale_models/

echo "=== Transferring pipeline scripts ==="
scp -i $KEY -O $OLD:/root/reels_r3/tts_gen3.py /root/reels_r3/
scp -i $KEY -O $OLD:/root/reels_r3/flux_gen5.py /root/reels_r3/
scp -i $KEY -O $OLD:/root/reels_r3/assemble5.py /root/reels_r3/
scp -i $KEY -O $OLD:/root/reels_r3/gen_bed_r3.py /root/reels_r3/
scp -i $KEY -O $OLD:/root/reels_r3/bed.wav /root/reels_r3/

echo "=== Transferring fonts ==="
scp -i $KEY -O $OLD:/usr/share/fonts/truetype/noto/NotoNaskhArabic* /tmp/ 2>/dev/null
cp /tmp/NotoNaskhArabic* /usr/share/fonts/truetype/noto/ 2>/dev/null
fc-cache -f 2>/dev/null

echo "=== TOTAL SIZE CHECK ==="
du -sh /root/ComfyUI/models/checkpoints/ /root/ComfyUI/models/text_encoders/ /root/ComfyUI/models/vae/ /root/ComfyUI/models/diffusion_models/ /root/ComfyUI/models/ipadapter/ /root/ComfyUI/models/upscale_models/ /root/reels_r3/

echo "=== TRANSFER COMPLETE ==="
