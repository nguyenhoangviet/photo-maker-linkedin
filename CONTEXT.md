# CONTEXT.md — LinkedIn Photo Maker

## What This App Does
Generates professional LinkedIn profile photos from any uploaded selfie or portrait.
All processing is local — no subscriptions, no API keys, no data leaves your machine.

**Core features:**
- Detects if the uploaded photo contains a human face (blocks landscapes, pets, etc.)
- Auto-detects gender (can be manually overridden)
- Removes the original background
- Replaces it with a professional solid color (10 presets + custom color picker)
- Optionally changes the outfit using local Stable Diffusion inpainting
- Outputs an 800×800 JPEG ready to upload to LinkedIn

---

## Tech Stack

### Backend
| Package | Version | Role |
|---------|---------|------|
| FastAPI | 0.111.0 | REST API framework |
| Uvicorn | 0.29.0 | ASGI server |
| Pillow | 10.3.0 | Image resizing, compositing, output |
| OpenCV (headless) | 4.9.0.80 | Face detection (Haar cascades) |
| NumPy | 1.26.4 | Array operations |
| rembg | 2.0.56 | Background removal (U2Net model) |
| DeepFace | 0.0.92 | Gender classification |
| tf-keras | 2.16.0 | DeepFace backend |
| mediapipe | 0.10.14 | Body pose landmarks for clothing mask |
| torch | ≥2.1.0 | Stable Diffusion inference backend |
| diffusers | 0.27.2 | Stable Diffusion Inpainting pipeline |
| transformers | 4.40.0 | Model tokenizers/encoders |
| accelerate | 0.30.0 | Memory optimization for inference |
| safetensors | ≥0.4.0 | Model loading format |

### Frontend
| Package | Version | Role |
|---------|---------|------|
| React | 18.3.1 | UI framework |
| Vite | 5.3.1 | Dev server + bundler |
| Tailwind CSS | 3.4.4 | Styling |
| Axios | 1.7.2 | HTTP client |

---

## File Structure

```
photo-maker-linkedin/
├── .github/
│   ├── copilot-instructions.md     ← Copilot coding instructions
│   └── workflows/
│       └── ci.yml                  ← GitHub Actions (lint + build)
│
├── backend/
│   ├── main.py                     ← FastAPI app + all routes
│   ├── requirements.txt            ← Python dependencies
│   ├── .env.example                ← No keys needed (placeholder)
│   ├── uploads/                    ← Runtime: uploaded images (gitignored)
│   ├── outputs/                    ← Runtime: generated results (gitignored)
│   └── services/
│       ├── __init__.py
│       ├── face_service.py         ← Face + gender detection
│       ├── background_service.py   ← Background removal + color composite
│       ├── body_mask_service.py    ← MediaPipe → clothing mask
│       └── generation_service.py  ← Stable Diffusion inpainting
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js              ← Proxies /api → localhost:8000
│   ├── tailwind.config.js          ← LinkedIn brand colors
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                 ← 3-step state machine
│       ├── index.css
│       └── components/
│           ├── UploadStep.jsx      ← Step 1: drag-drop + face analysis
│           ├── OptionsStep.jsx     ← Step 2: customize bg, outfit, gender
│           └── ResultStep.jsx      ← Step 3: preview + download
│
├── start-backend.sh                ← Creates venv, installs deps, starts uvicorn
└── start-frontend.sh               ← npm install + vite dev server
```

---

## API Reference

### `GET /api/options`
Returns all static option lists. Call on app mount.
```json
{
  "backgrounds": [{ "value": "classic_gray", "label": "Classic Gray", "color": "rgb(240, 240, 240)" }],
  "outfits": {
    "male": [{ "value": "business_suit", "label": "Business Suit" }],
    "female": [{ "value": "business_suit", "label": "Business Suit" }]
  },
  "genders": [{ "value": "male", "label": "Male" }, { "value": "female", "label": "Female" }],
  "sd_available": true
}
```

### `POST /api/analyze`
**Upload photo and run face + gender detection.**
Request: `multipart/form-data` with `file` field (JPEG/PNG/WebP, ≤10MB)
```json
{
  "session_id": "uuid-string",
  "face_count": 1,
  "gender": "male",
  "gender_confidence": 0.94,
  "preview": "data:image/jpeg;base64,...",
  "sd_available": true,
  "outfits": { "male": [...], "female": [...] }
}
```
Errors:
- `400` — unsupported type, too large, empty file, corrupt image
- `422` — `{"code": "NO_FACE_DETECTED", "message": "..."}`

### `POST /api/generate`
**Run the full photo generation pipeline.**
Request: `multipart/form-data`

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `session_id` | string | yes | — | From `/api/analyze` |
| `gender` | string | yes | — | `"male"` or `"female"` |
| `background_color` | string | no | `"classic_gray"` | Preset name |
| `custom_color_r` | int | no | — | 0–255, overrides preset |
| `custom_color_g` | int | no | — | 0–255, overrides preset |
| `custom_color_b` | int | no | — | 0–255, overrides preset |
| `outfit_style` | string | no | `"business_suit"` | See outfit options |
| `change_outfit` | bool | no | `false` | Requires diffusers installed |

```json
{
  "success": true,
  "result": "data:image/jpeg;base64,...",
  "outfit_applied": false,
  "download_url": "/api/download/uuid-string"
}
```

### `GET /api/download/{session_id}`
Returns the result as a downloadable `image/jpeg` file.
Content-Disposition: `attachment; filename=linkedin_photo_{short_id}.jpg`

---

## Local ML Pipeline

```
Photo upload
    │
    ▼
[1] Normalize — Pillow
    Resize to max 1024px, convert to JPEG

    │
    ▼
[2] Face Detection — OpenCV Haar Cascades
    haarcascade_frontalface_default.xml
    haarcascade_profileface.xml (fallback)
    ── No face? → HTTP 422 (blocked)

    │
    ▼
[3] Gender Detection — DeepFace + tf-keras
    CNN classification → "male" / "female" / "unknown"
    Confidence score 0–1
    ── User can override in UI

    │
    ▼
[4] Outfit Change (optional, change_outfit=true)
    │
    ├─ [4a] Clothing Mask — MediaPipe Pose
    │        33 body landmarks → torso polygon
    │        (shoulders, hips, elbows)
    │        Fallback: 25–80% height heuristic
    │
    └─ [4b] SD Inpainting — diffusers
             Model: runwayml/stable-diffusion-inpainting
             ├─ First run: downloads ~3.4GB to ~/.cache/huggingface/
             ├─ Device: CUDA (fp16) > MPS (fp16) > CPU (fp32)
             ├─ strength=0.85, guidance=7.5, steps=30, seed=42
             ├─ Attention slicing enabled (all devices)
             └─ xformers enabled if available (CUDA only)

    │
    ▼
[5] Background Removal — rembg (U2Net)
    Outputs RGBA with transparent background

    │
    ▼
[6] Color Background Composite — Pillow
    Alpha-composite onto chosen solid color
    Resize to 800×800 (LANCZOS)
    Sharpen 1.2×, contrast 1.05×
    Save as JPEG quality 92

    │
    ▼
800×800 JPEG result
```

---

## Background Color Presets

| Value | Label | RGB |
|-------|-------|-----|
| `classic_gray` | Classic Gray | (240, 240, 240) |
| `corporate_blue` | Corporate Blue | (31, 78, 121) |
| `navy` | Navy | (0, 32, 63) |
| `light_blue` | Light Blue | (173, 216, 230) |
| `white` | Pure White | (255, 255, 255) |
| `off_white` | Off White | (245, 245, 245) |
| `slate` | Slate | (112, 128, 144) |
| `dark_gray` | Dark Gray | (64, 64, 64) |
| `teal` | Teal | (0, 128, 128) |
| `forest_green` | Forest Green | (34, 85, 34) |

---

## Outfit Options

| Value | Male Prompt | Female Prompt |
|-------|------------|---------------|
| `business_suit` | Navy blazer, white dress shirt, tie | Navy blazer, white blouse |
| `business_casual` | Smart casual button-up shirt | Elegant smart casual blouse |
| `formal_suit` | Classic black formal suit | Black formal blazer suit |
| `blazer` | Charcoal grey blazer, collared shirt | Tailored grey blazer |

Negative prompt applied to all: `cartoon, illustration, anime, bad quality, blurry, distorted face, extra limbs, deformed, text, watermark, nsfw`

---

## Running Locally

```bash
# Terminal 1 — Backend
./start-backend.sh
# Starts on http://localhost:8000
# First run: installs Python deps + venv (~3 min)
# First outfit generation: downloads SD model (~3.4GB)

# Terminal 2 — Frontend
./start-frontend.sh
# Starts on http://localhost:5173
```

---

## CI / GitHub Actions

File: `.github/workflows/ci.yml`

**Backend job** (`ubuntu-latest`, Python 3.11):
- Installs lightweight deps only (no torch/diffusers/mediapipe — too large for CI)
- Runs `ruff check` (linting, ignores E501/F401)
- Runs `py_compile` on all service files

**Frontend job** (`ubuntu-latest`, Node 20):
- `npm install`
- `npm run build`
- Uploads `dist/` as artifact (7-day retention)

Triggers: push to `main`/`develop`, pull requests to `main`.

---

## Design Decisions

**Why no external APIs?**
All ML runs locally. No cost per image, no data privacy concerns, works offline after first model download.

**Why rembg instead of a custom segmentation model?**
U2Net in rembg is production-quality for portrait background removal with zero configuration.

**Why Stable Diffusion inpainting for outfit change?**
The only practical way to generate realistic clothing changes locally without an external API. The alternative (PNG clothing overlays) doesn't adapt to body shape/lighting.

**Why MediaPipe for the clothing mask?**
Lightweight, fast, and accurate for body pose — gives the SD model a precise region to inpaint rather than regenerating the whole image.

**Why session-based (file) storage instead of a database?**
It's a single-user local tool. File-based sessions are simpler, need no infrastructure, and auto-clean by simply deleting the directories.

**Why 800×800 output?**
LinkedIn's recommended profile photo dimensions. The circular crop LinkedIn applies looks best on a square image.
