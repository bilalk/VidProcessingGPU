# JSON Manifest Formats — OLD vs NEW

The pipeline supports **two** manifest schemas. They use **different scripts** and produce **different content**. Choose per batch.

---

## OLD format — "language-learning reel" (4-panel, ~60s)

Used by: `pipeline/flux/` (FLUX round) + `pipeline/ltx_v3/` (LTX FLF animation).

```json
{
  "reels": [
    {
      "id": "ar-en-025",
      "channel": "arabic-to-english",
      "pair": "ar-en",
      "topic": "acoustics",
      "seed": 41001,
      "voice_src":  "ar-SA-ZariyahNeural",
      "voice_tgt":  "en-US-JennyNeural",
      "voice_src2": "ar-SA-HamedNeural",
      "voice_tgt2": "en-US-GuyNeural",
      "music": "ambient acoustic oud ...",
      "words": [
        { "src": "همس", "tgt": "whisper", "translit": "hams" },
        { "src": "جدار", "tgt": "wall", "translit": "jidār" },
        { "src": "صوت", "tgt": "sound", "translit": "ṣawt" }
      ],
      "lines": [
        { "src": "كيف ... ؟", "tgt": "How ...?", "translit": "kayfa ..." },
        { "src": "...", "tgt": "...", "translit": "..." },
        { "src": "...", "tgt": "...", "translit": "..." }
      ],
      "scenes": [
        "wide shot ... cinematic film still, vertical composition",
        "same ... now ...",
        "same ... now ...",
        "same ... now ..."
      ]
    }
  ]
}
```

- **`words`**: exactly **3** objects `{src, tgt, translit}` (vocabulary).
- **`lines`**: exactly **3** objects `{src, tgt, translit}` (Q&A dialogue).
- **`scenes`**: exactly **4** prompt strings (FLUX keyframes s1–s4).
- **Flow**: TTS (3 lines × 2 voices + 3 words × 2) → FLUX 4 stills → **LTX FLF** animates s1→s2→s3→s4 (3 clips) → assemble mobile + desktop. ~60s.
- **`translit`** required for non-Latin (Arabic/Chinese) scripts.
- **Orientation rule**: for `english-to-X` channels, `src` = English, `tgt` = foreign (use `scripts/fix_srctgt.py` to fix inversions).
- Example files: `manifests/old/JSON_Aug28_1.json`, `manifests/renumbered/manifest_aug28_g1.json`.

---

## NEW format — "dramatic skit" (single-scene, ~7–9s)

Used by: `pipeline/v2/` (`tts_v2.py`, `flux_v2.py`, `assemble_v2.py`, `ltx_v2.py`).

```json
{
  "reels": [
    {
      "id": "ar-en-100",
      "channel": "arabic-to-english",
      "pair": "ar-en",
      "topic": "Airport Panic & Rescue",
      "seed": 51000,
      "voice_src":  "ar-SA-ZariyahNeural",
      "voice_tgt":  "en-US-JennyNeural",
      "voice_src2": "ar-SA-HamedNeural",
      "voice_tgt2": "en-US-GuyNeural",
      "music": "frenetic ...",
      "words": [ "أين", "جوازي", "Where", "passport" ],
      "lines": [
        { "id": 1, "speaker": "voice_src2", "text": "أين جوازي؟ لقد اختفى!", "start": 0.0, "end": 2.5 },
        { "id": 2, "speaker": "voice_tgt",  "text": "Where is my passport?", "start": 2.6, "end": 5.5 }
      ],
      "scenes": [
        { "scene_id": 1, "start_time": 0.0, "end_time": 5.5,
          "image_prompt": "...", "motion": "ken_burns_zoom_in_to_backpack", "audio_sync": "..." }
      ]
    }
  ]
}
```

- **`words`**: exactly **4 flat strings** = `[src1, src2, tgt1, tgt2]` (2 word pairs).
- **`lines`**: exactly **2** objects `{id, speaker, text, start, end}` — **explicit timing + speaker** (`speaker` ∈ `voice_src|voice_tgt|voice_src2|voice_tgt2`).
- **`scenes`**: exactly **1** object `{scene_id, start_time, end_time, image_prompt, motion, audio_sync}`.
- **Flow**: TTS (2 lines via `speaker` voice + 4 words) → FLUX **1** still from `image_prompt` → **LTX I2V** animates that single image (text prompt = `image_prompt + motion`) → assemble mobile + desktop. ~7–9s.
- **No `translit`** (dropped in this format).
- **Speaker↔text is self-consistent** (explicit `speaker` field) — no orientation ambiguity.
- Example file: `manifests/new/test.json`; renumbered: `manifests/renumbered/manifest_v2_100.json`.

---

## Renumbering (mandatory every batch)

Both formats keep `id` as the cache/output key. **Always renumber to fresh ids** before running, or stale caches (`img/`, `tts/`) will silently reuse old content.

- OLD format: `python scripts/renumber_aug28.py` (ids `059–082` style, seeds `41001+(nid-25)`).
- NEW format: `python scripts/renumber_100.py` (ids `100+`, seeds `51000+(nid-100)`).

The 6 channels are always:
`arabic-to-english`, `chinese-to-english`, `english-to-arabic`, `english-to-chinese`, `english-to-spanish`, `spanish-to-english`.

---

## Validation helpers
- `scripts/verify_aug28.py` / `scripts/validate_test.py` — schema + orientation checks.
- `scripts/fix_srctgt.py` — swaps `src`/`tgt` on `english-to-X` reels if inverted.
- `scripts/merge_aug28.py` — merges two 12-reel manifests into one 24-reel manifest.
