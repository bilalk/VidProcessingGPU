from huggingface_hub import hf_hub_download
import os

print("Downloading FLUX IP-Adapter model (XLabs-AI/flux-ip-adapter)...")
p1 = hf_hub_download(
    'XLabs-AI/flux-ip-adapter',
    'ip_adapter.safetensors',
    local_dir='/root/ComfyUI/models/ipadapter'
)
print(f"IP_ADAPTER_MODEL: {p1} ({os.path.getsize(p1)} bytes)")

print("Downloading FLUX IP-Adapter clip vision (image_encoder)...")
p2 = hf_hub_download(
    'XLabs-AI/flux-ip-adapter',
    'image_encoder.safetensors',
    local_dir='/root/ComfyUI/models/clip_vision'
)
print(f"CLIP_VISION: {p2} ({os.path.getsize(p2)} bytes)")
print("DONE")
