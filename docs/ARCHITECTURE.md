# 🏗️ REEL FACTORY — ARCHITECTURE DOCUMENT

**Last updated:** 2026-08-05 | **GPU:** AMD Instinct MI300X VF, 205.8 GB VRAM | **Server:** 129.212.180.144

---

## A. Core Architecture

### Client-Server Model

```
┌─────────────────────────────────┐     ┌──────────────────────────────────────┐
│        WINDOWS CLIENT           │     │         AMD GPU SERVER                │
│      (D:\ProjectComfy\reels)    │     │    (129.212.180.144:8188)            │
│                                 │     │                                      │
│  ┌───────────────────────────┐  │     │  ┌────────────────────────────────┐  │
│  │ manifest_*.json           │──┼──SSH─►│ /root/reels_r3/manifest.json    │  │
│  │ (reel definitions)        │  │ SCP  │ └────────────────────────────────┘  │
│  └───────────────────────────┘  │     │                                      │
│                                 │     │  ┌──────────┐  ┌──────────┐          │
│  ┌───────────────────────────┐  │     │  │ tts_gen3 │  │gen_bed_r3│          │
│  │ Pipeline scripts          │──┼──SSH─►│  │   .py    │  │   .py    │          │
│  │ (pushed once)             │  │ SCP  │  └────┬─────┘  └────┬─────┘          │
│  └───────────────────────────┘  │     │       │ edge-tts    │ numpy sine      │
│                                 │     │       ▼              ▼                │
│  ┌───────────────────────────┐  │     │  ┌──────────────────────┐            │
│  │ reels/<channel>/          │◄─┼─SCP──│  tts/       bed.wav   │            │
│  │   *.mp4                   │  │     │  └──────────┬───────────┘            │
│  └───────────────────────────┘  │     │             │                        │
│                                 │     │             ▼                        │
│                                 │     │  ┌──────────────────────┐            │
│                                 │     │  │     flux_gen_opt     │            │
│                                 │     │  │ burst-submits 48     │            │
│                                 │     │  │ prompts to ComfyUI   │            │
│                                 │     │  └──────────┬───────────┘            │
│                                 │     │             │                        │
│                                 │     │             ▼                        │
│                                 │     │  ┌──────────────────────┐            │
│                                 │     │  │   ComfyUI 0.29.0     │            │
│                                 │     │  │   FLUX.1-dev 768×1344│            │
│                                 │     │  │   /prompt API         │            │
│                                 │     │  └──────────┬───────────┘            │
│                                 │     │             │                        │
│                                 │     │             ▼                        │
│                                 │     │  ┌──────────────────────┐            │
│                                 │     │  │     assemble5.py     │            │
│                                 │     │  │  5-lane parallel:    │            │
│                                 │     │  │   1. zoompan segments │            │
│                                 │     │  │   2. ASS subtitle burn│            │
│                                 │     │  │   3. audio mix        │            │
│                                 │     │  │   4. QA check         │            │
│                                 │     │  └──────────┬───────────┘            │
│                                 │     │             │                        │
│                                 │     │             ▼                        │
│                                 │     │  ┌──────────────────────┐            │
│                                 │     │  │  out/<channel>/       │            │
│                                 │     │  │  *.mp4 + .ass + .txt │            │
│                                 │     │  └──────────────────────┘            │
│                                 │     │                                      │
└─────────────────────────────────┘     └──────────────────────────────────────┘
```

**Key design decisions:**
- Client is **thin** — only manifests + result storage. All compute on GPU server.
- Server scripts are **manifest-driven** — the same code processes any valid JSON.
- Pipeline stages are **independently cacheable** — TTS, FLUX, assembly each skip completed work.
- Workspaces are **isolated** — parallel batches get their own `/root/reels_r5_w01/`, `/root/reels_r5_w02/`.

---

## B. Tech Stack

### Server (GPU Compute)

| Layer | Component | Purpose |
|---|---|---|
| OS | Ubuntu 24.04 LTS | Base system |
| GPU Runtime | ROCm 7.2.4, PyTorch 2.13.0+rocm7.2 | AMD GPU acceleration |
| Image Gen | ComfyUI 0.29.0 + FLUX.1-dev | Text-to-image, 768×1344, 16 steps, ~4.3s/image |
| Video Gen | Wan 2.1 T2V 14B (installed, not active) | Text-to-video hook clips (disabled due to mux corruption) |
| TTS | edge-tts 7.2.8 | Neural voice generation, 4 languages × 2-3 voices each |
| Music | numpy (gen_bed_r3.py) | Procedural ambient music via sine wave synthesis |
| Assembly | ffmpeg 6.1.1 + libass | Zoompan Ken Burns effect, ASS subtitle burn, audio mux |
| IP-Adapter | XLabs-Flux + insightface | Face consistency (models installed, pipeline not automated) |
| Orchestration | Bash + Python | Stage-based pipeline with error handling |
| API Transport | urllib (stdlib) | Direct HTTP to ComfyUI REST API |
| Fonts | Noto Sans, Noto Sans CJK SC, Noto Naskh Arabic | Multilingual subtitle rendering |
| RDP | xrdp + xorgxrdp | Remote desktop access |

### Client (Windows)

| Layer | Component | Purpose |
|---|---|---|
| Storage | D:\ProjectComfy\reels\ | Manifest staging + result delivery |
| Transfer | OpenSSH SCP (`scp -O`) | Manifest push, result pull |
| Content | Fable 5 / Gemini / Kimi (external) | Manifest generation (words, dialogs, scenes, music prompts) |

### Models on Disk

| Model | Size | Purpose |
|---|---|---|
| flux1-dev.safetensors | 23 GB | Image generation |
| t5xxl_fp8_e4m3fn.safetensors | 4.6 GB | FLUX text encoder |
| clip_l.safetensors | 235 MB | FLUX CLIP encoder |
| ae.safetensors | 320 MB | FLUX VAE |
| wan2.1_t2v_14B_fp8_scaled.safetensors | 14 GB | Video generation (idle) |
| wan2.1_i2v_480p_14B_fp8_scaled.safetensors | 16 GB | Image-to-video (idle) |
| wan2.1_i2v_720p_14B_fp8_scaled.safetensors | 16 GB | High-res image-to-video (idle) |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | 6.3 GB | Wan text encoder |
| wan_2.1_vae.safetensors | 243 MB | Wan VAE |
| flux-ip-adapter.safetensors | 937 MB | FLUX IP-Adapter |
| model.safetensors (CLIP-ViT-L) | 1.6 GB | IP-Adapter vision encoder |
| 4x-UltraSharp.pth | 64 MB | Image upscaler |
| **Total models** | **~88 GB** | |

---

## C. Core Flow

### Single Batch (12 reels) — End to End

```
1. CONTENT CREATION (External — Fable 5 / Gemini)
   └── Produces manifest.json with 12 reel definitions:
       - id, channel, voice assignments, 3 words, 3 dialog lines, 4 scene prompts, music prompt

2. MANIFEST VALIDATION (Client)
   └── python r3_validate.py → checks schema, word uniqueness, channel distribution

3. PUSH TO SERVER
   └── scp manifest.json root@GPU_SERVER:/root/reels_r3/

4. PIPELINE EXECUTION (Server — run_r3.sh)
   │
   ├── STAGE 1: TTS (tts_gen3.py)
   │   └── 12 reels × (3 lines × 2 voices + 3 words × 2 voices) = 144 MP3s
   │   └── edge-tts --rate=-10% --voice <voice> --text <text>
   │   └── Cache: skips if MP3 > 2000 bytes exists
   │   └── Time: ~2 min (cached ~0s)
   │
   ├── STAGE 2: Music Bed (gen_bed_r3.py)
   │   └── Generates 3-min ambient sine-wave loop → bed.wav
   │   └── Cache: skips if bed.wav exists
   │
   ├── STAGE 3: FLUX Images (flux_gen_opt.py)
   │   └── 12 reels × 4 scenes = 48 images
   │   └── Burst-submits ALL 48 to ComfyUI /prompt API at once
   │   └── Polls /history/{pid} for each
   │   └── Downloads PNGs via /view
   │   └── Cache: skips PNG > 100KB
   │   └── Time: ~167s (48 × ~3.5s, queued back-to-back)
   │
   └── STAGE 4: Assembly (assemble5.py)
       └── 5-lane ThreadPoolExecutor parallel
       └── Per reel:
           ├── build_timeline() → reads real TTS durations via ffprobe
           ├── make_ass() → generates ASS subtitle file
           ├── build_seg() × 4 → zoompan Ken Burns from PNG → h264 segment
           ├── Subtitle burn → ffmpeg concat segs + ass filter → vsub.mp4
           ├── Audio mix → 12 voice MP3s + bed.wav → amix + loudnorm
           └── Final mux → vsub + audio → h264+AAC MP4
       └── QA: ffprobe check → h264, 1080×1920, AAC, duration ≥ 29.5s
       └── Export: mp4 + .ass + .script.txt
       └── Time: ~55s

5. PULL RESULTS (Client)
   └── scp -O *.mp4 D:\ProjectComfy\reels\<channel>\  (ONE stream at a time)

TOTAL PER 12-REEL BATCH: ~4-5 min
```

### Parallel Batch (N × 12 reels)

```
launch_r5.sh
├── Splits manifest into N slices
├── Creates isolated workspace per slice (/root/reels_r5_w01/, w02/, ...)
├── Copies all scripts into each workspace (sed-patches ROOT path)
├── Launches all workspaces simultaneously via setsid
│   ├── TTS: parallel (edge-tts is CPU-bound, runs concurrently fine)
│   ├── FLUX: all 96+ jobs serialized by ComfyUI queue → GPU runs at 100%
│   └── Assembly: MUST run sequentially (ffmpeg fd limit = 1024)
└── Pulls from all workspace out/ dirs
```

### GPU Utilization Profile (12-reel batch)

```
                    TTS    Idle   FLUX (burst 48)     Assembly
GFX%:   ░░░░     ░░░░    ░░░░  ████████████████████  ░░░░
VRAM:   ~0.3GB   ~30GB   ~30GB  ~30GB                ~30GB
Time:   0-2min    2-5min  5-8min                      8-10min
```

GPU is bottlenecked by **single ComfyUI queue serialization** — the queue processes 1 FLUX job at a time. 96 queued jobs run back-to-back with 0 idle time, but no jobs run in parallel. This is a ComfyUI architectural limitation, not a GPU limitation.

---

## D. Pivot Readiness Assessment

### Pivot 1: E-commerce Product Viral Video System

**Goal:** Input raw product images → output 30s persuasive product video with voice-over, music, Ken Burns motion, text overlays.

**Foundation already built:**

| Capability | Status | Gap |
|---|---|---|
| Image input → video pipeline | ✅ Assemble5 already does `-loop 1 -i img.png` zoompan | Need to accept arbitrary PNGs, not FLUX-generated |
| Ken Burns zoom/pan | ✅ 4 camera moves already coded (ZOOMS array) | Preset moves are fine for product showcase |
| Text overlay (ASS subtitles) | ✅ Full ASS generation with styled text, positioning | Replace language-learning layout with product specs/pricing |
| Voice-over (TTS) | ✅ edge-tts with 12+ neural voices | Use single English voice, different prompt schema |
| Background music | ✅ gen_bed_r3.py procedural bed | Same — loop under voice |
| h264+AAC output | ✅ Working, verified | Directly reusable |

**What needs new code:**
1. **New manifest schema** — `product_name`, `price`, `features[3]`, `cta_text`, `source_images[4]` instead of words/lines/scenes
2. **New TTS script** — reads product features from manifest, generates single-voice narration
3. **New assemble script** — product-appropriate subtitle layout, pricing overlay, CTA screen at end
4. **Image input** — bypass FLUX entirely, use client-provided images (scp upload)
5. **FFmpeg transitions** — crossfade between product images instead of Ken Burns only

**Foundation score: 7/10** — Image pipeline, voice, music, subtitle, mux all exist. Only manifest + image input paths are new.

---

### Pivot 2: Cartoon-Style Product Illustration Reels

**Goal:** 30-40s cartoon/anime-style product demonstration reel with illustrated characters.

**Foundation already built:**

| Capability | Status | Gap |
|---|---|---|
| FLUX image generation | ✅ Working | Add "anime style, flat vector illustration, cartoon" to prompts |
| Prompt-driven image pipeline | ✅ Manifest → scenes → FLUX → assemble | Add style tokens to every scene prompt |
| Ken Burns + subtitles | ✅ Working | Same layout but cartoon-appropriate fonts |
| Consistent character pipeline | ✅ Text-based consistency works | Needs IP-Adapter automation for same character faces |
| Wan animation | ⚠️ Model installed, mux bugged | Would be perfect for cartoon character animation |

**What needs new code:**
1. **New prompt template for Fable 5** — cartoon-specific scene descriptions (vector art, flat colors, expressive faces, speech bubbles)
2. **Wan animation fix** — the concat mux issue must be solved before using Wan for character animation
3. **IP-Adapter automation** — upload 1 reference character image → IP-Adapter conditions all FLUX outputs to same face
4. **Cartoon-optimized ASS template** — speech bubbles, comic-sans-like fonts, colorful text outlines

**Foundation score: 6/10** — FLUX + IP-Adapter + Wan stack is already on disk. Prompt engineering is the main new work.

---

### Pivot 3: Animated Cartoon Character Reels (Funny/Informative)

**Goal:** Animated cartoon characters delivering funny or informative content in 30-40s reels.

**Foundation already built:**

| Capability | Status | Gap |
|---|---|---|
| Wan 2.1 T2V animation | ⚠️ Model installed (14GB), flicker fixed (cfg=1.0), mux bug present | Fix concat mux OR use Wan as full-reel generator |
| FLUX still-image generation | ✅ Working | Cartoon characters via prompt engineering |
| Multi-voice TTS | ✅ 12+ voices | Character A = voice X, Character B = voice Y |
| ASS subtitle positioning | ✅ `\pos(x,y)` overrides working | Character dialogue boxes at different screen positions |
| IP-Adapter consistency | ⚠️ Models installed | Reference character image → same face across Wan + FLUX frames |

**What needs new code:**
1. **Fix Wan concat mux** — the most critical blocker. Without it, Wan clips can't be spliced into timeline
2. **Wan-driven pipeline** — generate the ENTIRE reel as one Wan clip (30s continuous) instead of 4 still panels
3. **Character voice mapping** — manifest schema with character-to-voice assignments
4. **Multi-character ASS** — multiple subtitle styles for different speakers
5. **Lip-sync** — wav2lip and LatentSync custom nodes are INSTALLED on server. Lip-sync is possible.

**Foundation score: 5/10** — The hardest part (Wan mux) isn't solved. But if Wan works as a standalone full-reel generator (bypassing ffmpeg concat), then voice + subtitle + lip-sync are all install-ready.

---

## Summary

| Pivot | Foundation Ready | Main Blockers | Effort Estimate |
|---|---|---|---|
| E-commerce product videos | **7/10** | New manifest schema, image upload path | Low — 1-2 new Python scripts |
| Cartoon product illustrations | **6/10** | IP-Adapter automation, Wan mux fix | Medium — prompt engineering + pipeline scripting |
| Animated cartoon reels | **5/10** | Wan mux fix OR full-reel Wan generation | High — Wan is critical but unstable |

**What you can do TODAY without any code changes:**
- Take a product image, place it at `D:\ProjectComfy\reels\<channel>\`, and visually inspect — the zoompan + subtitle + voice pipeline already works for arbitrary still images
- Change the FLUX prompt suffix in any manifest from "cinematic film still" to "flat vector cartoon illustration, vibrant colors, bold outlines" — FLUX will generate cartoon-style images
- Use `es-en-041.mp4` or similar existing reels as proof-of-concept — they already show multi-panel still images with voice-over, subtitles, music, and Ken Burns motion. The foundation works.
---

## E. Scene-Prompt Split (FLUX still vs LTX motion) — added 2026-08-28

### Why
Each `scenes[k]` string now carries **two** kinds of instruction in one field:

```
<base scene description>, LTX motion: <camera/motion guidance>[, <mood>], cinematic film still, vertical composition
```

- The **base + "cinematic film still, vertical composition"** is what FLUX needs (a clean still image with framing).
- The **"LTX motion: …"** part is motion guidance only LTX-2.3 can honor.

Passing the whole string to *both* models degrades both: FLUX sees irrelevant motion text (for a still it can't produce), and LTX sees "cinematic film still" (which contradicts actual motion) plus framing tokens.

### The split (implemented in code)
| Model | Transform | Result |
|---|---|---|
| **FLUX** (`flux_gen5.py`, `flux_gen_opt.py`) | strip `,LTX motion: …` up to `,cinematic film still` | clean still prompt |
| **LTX** (`run_ltx_v3.py`) | remove `cinematic film still` / `vertical composition` / `horizontal composition`; relabel `LTX motion:` → `Camera motion:` | motion-aware prompt |

### Rules for future agents / manifest authors
1. Keep the exact marker `LTX motion: ` in scene prompts — the split regex depends on it.
2. Always end scenes with `, cinematic film still, vertical composition` (mobile) — FLUX framing + the split's right boundary.
3. Desktop uses `horizontal composition`; `run_ltx_v3.py` auto-swaps `vertical`→`horizontal` for desktop prompts.
4. Put realism tokens (e.g. "realistic particle physics", "realistic heat distortion") inside the motion block so they bias LTX motion; FLUX stills keep them out.

### New manifest ID ranges (Aug-28 batch)
- `JSON_Aug28_1.json` → renumbered `059–070` (fresh seeds 41035–41046)
- `JSON_Aug28_2.json` → renumbered `071–082` (seeds 41047–41058)

*(Renumbering is mandatory because both source files reuse ids 025–026/41001–41012, and the server already has stale caches for those ids.)*

---

## F. LTX-2.3 Video Pipeline (current production line) — updated 2026-08-28

### Engine
| Item | Value |
|---|---|
| Video model | **LTX-2.3 22B distilled-fp8** (`ltx-2.3-22b-distilled-fp8.safetensors`, 29.5 GB) |
| Text encoder | **Gemma-3 12B** (`gemma_3_12B_it_fp4_mixed.safetensors`) — NOT `gemma_2` (prior typo, do not regress) |
| Audio | LTX-2 is an AV model (native lip-synced audio present in the graph, but currently overridden by edge-tts + bed) |
| Runtime | ComfyUI 0.30.0 native LTX nodes (`LTXAVTextEncoderLoader`, `EmptyLTXVLatentVideo`, `LTXVConditioning`, `LTXVAddGuide`, `VAEDecodeTiled`, …) |
| Sampling | distilled ~9 sigmas (ManualSigmas), Euler-Ancestral, cfg 1.0 |

### Flow (FLF = First/Last-Frame)
```
FLUX.1-dev keyframes s1..s4  (768×1344 mobile / 1344×768 desktop)
   → LTX-2.3 animates BETWEEN each pair (s1→s2, s2→s3, s3→s4) @24fps
   → 3 animated clips + 1 zoompan recap panel per reel
   → assemble mobile 1080×1920  +  desktop 1920×1080 (TRUE horizontal, NOT blur-pad)
```
- Keyframes are **shared** with the FLUX round (cached in `/root/reels_r3/img/`), so LTX adds only the animation cost.
- Orchestrator `run_ltx_v3.py` processes **ONE channel per invocation** (single ComfyUI queue; burst-submitting >~50 LTX jobs risks a queue-wipe soft-restart).
- Output dirs: `out_v3_mobile/` (9:16) + `out_v3_desktop/` (16:9). `.done` markers in `done_v3/`.

### Prompt split (see §E)
`still_prompt()` (FLUX) strips `LTX motion: …`; `ltx_prompt()` (LTX) drops `cinematic film still`/`composition` and relabels `LTX motion:` → `Camera motion:`. Desktop automatically uses horizontal framing via dimensions (1344×768), not text.

### LTX-Desktop (evaluated, NOT adopted)
Lightricks/LTX-Desktop is a GUI non-linear editor, Apache-2.0, ~1.9k ★ — but **local generation is NVIDIA + Apple-Silicon only**. On AMD (our MI300X) it falls back to **fal.ai API mode (paid key + credits)**, bypassing our GPU. **ComfyUI is the correct headless engine for AMD.** No model-gating/key blockers: LTX-2 22B is openly downloadable (Apache-2.0 code; model weights under Lightricks license).

### Blank-GPU reinstall (for a fresh MI300X droplet)
The full from-scratch install script is **`_scripts/setup_new_gpu2.sh`** (venv → PyTorch ROCm 7.2 → ComfyUI deps → RDP → Noto fonts → model dirs → systemd `comfyui.service`). Model weights are downloaded separately to `/root/ComfyUI/models/` (see `transfer_models.sh` for server-to-server copy). Pipeline scripts are pushed from `_scripts/` via scp. A new JSON manifest can drop-in replace `manifest_aug28_*.json` — the pipelines are manifest-driven (no per-batch code changes needed beyond renumbering to fresh IDs).

