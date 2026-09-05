# REEL JSON FORMAT STANDARD — verified against the live pipeline (Sept 6, 2026)

## VERDICT: use the **29aug** format (= `29Aug2.json`). It is the pipeline's native format.

Code evidence chain (no code was modified, only read):
1. `C:\ReelFactoryWeb\pipeline.py` → `detect_format()`: `term` in words = **29aug**; `src`+`tgt` = aug28.
2. `pipeline.py` → `normalize()` line ~151: for 29aug it does `words = [{'src': w['term'], 'tgt': w['translation']}]` — **no swap for any channel**. For aug28 it SWAPS words and flips narration for english-to-* channels.
3. Server `/root/reels_r3/tts_29.py` lines 16-22: `vf`(=voice_src, foreign voice) speaks `words[].src`; `ve`(=voice_tgt, English voice) speaks `words[].tgt` + the 3 narration lines.
4. Server `/root/reels_r3/assemble_29.py` line ~29: `float(ffprobe stdout)` → any **0-byte mp3 = ValueError = whole 12-reel group aborted**.

**Invariant the whole system depends on (all 6 channels, no exceptions):**
`words[].src` = FOREIGN word • `words[].tgt` = ENGLISH meaning • `narration` = 3 ENGLISH strings • `voice_src` = foreign voice • `voice_tgt` = English voice.

Since the 29aug path never swaps, **the input file must already obey this invariant**: `term` = foreign word, `translation` = English — even for `english-to-arabic/chinese/spanish` channels. The channel name never flips word direction.

## Compliance scorecard (produced by running the real pipeline.normalize() on each file — see verify_out.txt)

| File | Detected | Structure | Direction-correct? | Result |
|---|---|---|---|---|
| **29Aug2.json** | 29aug | PASS | **12/12 reels correct** (incl. en-ar Arabic terms, en-zh Chinese terms, en-es Spanish terms) | **THE GOLDEN REFERENCE** |
| REEL_TEMPLATE_29aug.json | 29aug | PASS | 6/6 correct | The template to hand to the next agent |
| JSON_Aug28_2.json | aug28 | PASS | **6/12 WRONG** — its english-to-* reels put FOREIGN in `src` and foreign text in `lines.src`; the aug28 swap then hands Arabic/Chinese/Spanish to the ENGLISH voice + foreign narration | Would ALSO collapse if fed |
| gemini-...744501.json (fed as file A) | 29aug | PASS | **en-zh ×2 INVERTED** (term=impatience/compound/mastery → translation=急躁/复利/精通), en-es ×2 inverted | en-zh-038 t1/t2/t3 = **0 bytes** (verified on server) → assemble crash → **6 reels missed** (038/039 fatal + 040/041/042/043 collateral) |
| gemini-...792019.json (fed as file B) | 29aug | PASS | en-es ×2 inverted (Spanish in translation), rest correct | No Chinese inversion → no 0-byte crash → all 12 assembled, but en-es-050/051 have English voice mangling Spanish (the "TTS incorrectness") |

## What the next agent must produce (per file, 2 files per job)
- Top level: `{ "reels": [ ... 12 reels ... ] }` (extra top-level keys like `_RULES` are ignored safely).
- Per reel keys (all required): `id` (placeholder ok, pipeline renumbers), `channel`, `pair`, `topic` (fresh kebab-case), `seed` (int), `voice_src`, `voice_tgt`, `voice_src2`, `voice_tgt2`, `music` (1 English mood string), `words` (×3), `lines` (×3), `scenes` (×4).
- `words[]`: `{ "term": "<FOREIGN word>", "translit": "<latin reading, for ar/zh>", "translation": "<English meaning>" }`
- `lines[]`: 3 plain ENGLISH strings — hook question, fact, call-to-action.
- `scenes[]`: `{ "scene_index": 1-4, "shot_type": "...", "ltx_motion_profile": "<motion/physics ONLY>", "prompt": "<English image prompt, consistent character across all 4 scenes, ends with ', cinematic film still, vertical composition'>" }` — **never** write `LTX motion:` inside `prompt` (pipeline appends it).

## Fixed voice table (copy exactly)
| channel | pair | voice_src | voice_tgt | voice_src2 | voice_tgt2 |
|---|---|---|---|---|---|
| arabic-to-english | ar-en | ar-SA-ZariyahNeural | en-US-JennyNeural | ar-SA-HamedNeural | en-US-GuyNeural |
| chinese-to-english | zh-en | zh-CN-XiaoxiaoNeural | en-US-JennyNeural | zh-CN-YunxiNeural | en-US-GuyNeural |
| spanish-to-english | es-en | es-ES-ElviraNeural | en-US-JennyNeural | es-ES-AlvaroNeural | en-US-GuyNeural |
| english-to-arabic | en-ar | en-US-JennyNeural | ar-SA-ZariyahNeural | en-US-GuyNeural | ar-SA-HamedNeural |
| english-to-chinese | en-zh | en-US-JennyNeural | zh-CN-XiaoxiaoNeural | en-US-GuyNeural | zh-CN-YunxiNeural |
| english-to-spanish | en-es | en-US-JennyNeural | es-ES-ElviraNeural | en-US-GuyNeural | es-ES-AlvaroNeural |

(voice_src = FROM-language voice, voice_tgt = TO-language voice; pipeline swaps english-to-* itself.)

## Pre-flight check (10 seconds, prevents every collapse)
Run before uploading any new pair of files:
```
python C:\Users\faraz\Desktop\verify_with_pipeline.py
```
(add your new file paths to FILES) — it runs the REAL `pipeline.detect_format/validate/normalize` and prints FATAL for any reel where the English voice would receive non-English text (= 0-byte TTS = missed reels) — or just eyeball: **every `term` must be non-English, every `translation`/`lines` must be English, in every channel.**
