from huggingface_hub import hf_hub_download
import os, shutil

# 1. Rename already-downloaded model to correct name
src = '/root/ComfyUI/models/ipadapter/ip_adapter.safetensors'
dst = '/root/ComfyUI/models/ipadapter/flux-ip-adapter.safetensors'
if os.path.exists(src) and not os.path.exists(dst):
    shutil.move(src, dst)
    print(f"RENAMED: {src} -> {dst}")

# 2. Download CLIP vision model (openai/clip-vit-large-patch14)
# XLabs uses this specific CLIP model for the IPAdapter
print("Downloading CLIP vision model (openai/clip-vit-large-patch14)...")
p = hf_hub_download(
    'openai/clip-vit-large-patch14',
    'model.safetensors',
    local_dir='/root/ComfyUI/models/ipadapter'
)
print(f"CLIP_VISION: {p} ({os.path.getsize(p)} bytes)")

# Verify both files exist
for f in ['flux-ip-adapter.safetensors', 'model.safetensors']:
    path = os.path.join('/root/ComfyUI/models/ipadapter', f)
    if os.path.exists(path):
        print(f"  OK: {f} ({os.path.getsize(path)} bytes)")
    else:
        print(f"  MISSING: {f}")

print("SETUP COMPLETE")
