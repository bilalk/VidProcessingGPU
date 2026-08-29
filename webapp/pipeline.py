# pipeline.py — format detection, validation, dedup, normalization, renumbering.
# Pure logic (no network); produces the canonical 29aug manifest the deployed
# server scripts (tts_29.py / flux_gen_opt.py / assemble_29.py / ltx_29.py) consume.

import json, os, re, glob

CHANNELS = ['arabic-to-english', 'chinese-to-english', 'english-to-arabic',
            'english-to-chinese', 'english-to-spanish', 'spanish-to-english']
X2EN = {'arabic-to-english', 'chinese-to-english', 'spanish-to-english'}
EN2X = {'english-to-arabic', 'english-to-chinese', 'english-to-spanish'}

# Where past manifests live (the "topic database" for dedup + the id range for renumber).
PAST_DIRS = [r'C:\ProjectComfy\reels']             # recursive
PAST_DIRS_TOPLEVEL = [r'C:\ProjectComfy']           # *.json at top level only (29Aug1.json etc.)


def nonlatin(s):
    return any(ord(c) > 0x7F for c in str(s))


def load_json(path):
    return json.load(open(path, encoding='utf-8'))


def detect_format(reels):
    """Return '29aug' | 'aug28' by inspecting the first word object."""
    for r in reels:
        w0 = (r.get('words') or [{}])[0] if isinstance(r.get('words'), list) else {}
        if not isinstance(w0, dict):
            continue
        if 'term' in w0:
            return '29aug'
        if 'src' in w0 and 'tgt' in w0:
            return 'aug28'
    return None


def validate(reels):
    issues = []
    if not isinstance(reels, list) or len(reels) == 0:
        return ['no "reels" array']
    for r in reels:
        rid = r.get('id', '?')
        for f in ['id', 'channel', 'pair', 'topic', 'seed',
                  'voice_src', 'voice_tgt', 'voice_src2', 'voice_tgt2',
                  'music', 'words', 'lines', 'scenes']:
            if f not in r:
                issues.append(f'{rid}: missing "{f}"')
        if r.get('channel') not in CHANNELS:
            issues.append(f'{rid}: unknown channel "{r.get("channel")}"')
        if len(r.get('words', [])) != 3:
            issues.append(f'{rid}: words={len(r.get("words", []))} (need 3)')
        if len(r.get('lines', [])) != 3:
            issues.append(f'{rid}: lines={len(r.get("lines", []))} (need 3)')
        if len(r.get('scenes', [])) != 4:
            issues.append(f'{rid}: scenes={len(r.get("scenes", []))} (need 4)')
    return issues


def _iter_manifests(dirs, toplevel_dirs):
    for d in dirs:
        for p in glob.glob(os.path.join(d, '**', '*.json'), recursive=True):
            yield p
    for d in toplevel_dirs:
        for p in glob.glob(os.path.join(d, '*.json')):
            yield p


def collect_past_topics(dirs=None, toplevel=None, exclude=()):
    dirs = dirs or PAST_DIRS
    toplevel = toplevel or PAST_DIRS_TOPLEVEL
    used = set()
    for p in _iter_manifests(dirs, toplevel):
        if os.path.basename(p) in exclude:
            continue
        try:
            data = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        for r in data.get('reels', []):
            t = r.get('topic')
            if t:
                used.add(t)
    return used


def check_dedup(reels, used):
    """used = set of already-used topics. Returns list of redundant topic strings."""
    return [r.get('topic') for r in reels if r.get('topic') in used]


def collect_used_ids(dirs=None, toplevel=None):
    dirs = dirs or PAST_DIRS
    toplevel = toplevel or PAST_DIRS_TOPLEVEL
    used = set()
    for p in _iter_manifests(dirs, toplevel):
        try:
            data = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        for r in data.get('reels', []):
            m = re.match(r'^.+?-(\d+)$', str(r.get('id', '')))
            if m:
                used.add(int(m.group(1)))
    return used


def find_next_start_id(dirs=None, toplevel=None):
    used = collect_used_ids(dirs, toplevel)
    return (max(used) + 1) if used else 0


def normalize(reels, fmt, start_id):
    """Convert either input format into the canonical 29aug manifest.
    Canonical invariants: voice_src/words.src = FOREIGN, voice_tgt/words.tgt = ENGLISH,
    'narration' = 3 English strings, 'scenes' = 4 strings with 'LTX motion:' markers.
    """
    out = []
    nid = start_id
    for ch in CHANNELS:
        for r in reels:
            if r.get('channel') != ch:
                continue
            num = nid
            nid += 1
            rid = f"{r['pair']}-{num:03d}"
            is_en2x = r['channel'] in EN2X

            vs, vt = r['voice_src'], r['voice_tgt']
            vs2, vt2 = r['voice_src2'], r['voice_tgt2']
            if is_en2x:
                vs, vt = vt, vs
                vs2, vt2 = vt2, vs2

            nr = {
                'id': rid,
                'channel': r['channel'],
                'pair': r['pair'],
                'topic': r.get('topic', ''),
                'seed': 62000 + num,
                'music': r.get('music', ''),
                'voice_src': vs,
                'voice_tgt': vt,
                'voice_src2': vs2,
                'voice_tgt2': vt2,
            }

            if fmt == '29aug':
                words = [{'src': w['term'], 'tgt': w['translation']} for w in r['words']]
                narration = [str(x) for x in r['lines']]
                scenes = [f"{s['prompt']}, LTX motion: {s['ltx_motion_profile']}" for s in r['scenes']]
            else:  # aug28
                words = [{'src': w['src'], 'tgt': w['tgt']} for w in r['words']]
                narration = [ln['tgt'] if not is_en2x else ln['src'] for ln in r['lines']]
                if is_en2x:
                    words = [{'src': w['tgt'], 'tgt': w['src']} for w in words]
                scenes = [str(x) for x in r['scenes']]

            nr['words'] = words
            nr['narration'] = narration
            nr['scenes'] = scenes
            out.append(nr)
    return out
