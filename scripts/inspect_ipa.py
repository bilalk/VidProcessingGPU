import json
from huggingface_hub import hf_hub_download

p = hf_hub_download('XLabs-AI/flux-ip-adapter', 'ip_adapter_workflow.json', local_dir='/tmp/flux_ipa')
w = json.load(open(p))
print("=== NODES ===")
print(f"Type: {type(w)}")
if isinstance(w, dict):
    for nid, node in w.items():
        if isinstance(node, dict):
            ct = node.get('class_type','')
            inp = list(node.get('inputs',{}).keys())
            print(f"{nid}: {ct} => {inp}")
        else:
            print(f"{nid}: {node}")
