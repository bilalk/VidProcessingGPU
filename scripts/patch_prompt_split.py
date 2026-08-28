import sys

def patch(path, edits):
    s = open(path, encoding='utf-8').read()
    for old, new, exp in edits:
        n = s.count(old)
        if n != exp:
            print(f"[FAIL] {path}: {old[:60]!r} found {n}x expected {exp}")
            sys.exit(1)
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
    print(f"[OK] patched {path}")

STILL = '''
def still_prompt(s):
    # FLUX still: strip the "LTX motion: ..." directive (between it and "cinematic film still")
    # so the image model gets a clean still, not motion instructions it cannot render.
    i = s.find('LTX motion:')
    if i == -1:
        return s
    j = s.find('cinematic film still', i)
    if j == -1:
        return s
    head = s[:i].rstrip(', ')
    return (head + ', ' + s[j:]) if head else s[j:]
'''

LTX = '''
def ltx_prompt(s):
    # LTX motion prompt: drop still/framing tokens, relabel the motion directive
    p = s.replace('LTX motion:', 'Camera motion:')
    for tok in ('cinematic film still', 'vertical composition', 'horizontal composition'):
        p = p.replace(tok, '')
    while ',,' in p:
        p = p.replace(',,', ',')
    return p.strip(' ,')
'''

# 1) FLUX generator (this round's workhorse)
patch('/root/reels_r3/flux_gen_opt.py', [
    ('def build(prompt, seed, prefix):',
     STILL + '\ndef build(prompt, seed, prefix):', 1),
    ('build(scene, seed, prefix)',
     'build(still_prompt(scene), seed, prefix)', 1),
])

# 2) Also patch flux_gen5.py (sequential fallback) so it stays consistent
patch('/root/reels_r3/flux_gen5.py', [
    ('def build(prompt, seed, prefix):',
     STILL + '\ndef build(prompt, seed, prefix):', 1),
    ('build(scene, seed, prefix)',
     'build(still_prompt(scene), seed, prefix)', 1),
])

# 3) LTX orchestrator (used next round)
patch('/root/reels_ltx/run_ltx_v3.py', [
    ('def horizontal_prompt(s):',
     LTX + '\ndef horizontal_prompt(s):', 1),
    ("prompt_m=r['scenes'][k]",
     "prompt_m=ltx_prompt(r['scenes'][k])", 1),
    ("prompt_d=horizontal_prompt(r['scenes'][k])",
     "prompt_d=ltx_prompt(r['scenes'][k])", 1),
])

print('ALL PATCHES DONE')
