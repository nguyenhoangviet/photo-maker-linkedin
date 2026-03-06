# LinkedIn Photo Maker — Copilot Instructions

## Project Overview
Full-stack app that generates professional LinkedIn profile photos entirely locally.
No external APIs or API keys. All ML models run on the user's machine.

## Architecture
- **Backend:** FastAPI (Python 3.11) on `localhost:8000`
- **Frontend:** React 18 + Vite + Tailwind CSS on `localhost:5173`
- Vite proxies `/api/*` → backend, so never hardcode `localhost:8000` in frontend code

## Backend Structure

```
backend/
├── main.py                  # All FastAPI routes
└── services/
    ├── face_service.py      # Face detection (OpenCV) + gender detection (DeepFace)
    ├── background_service.py# Background removal (rembg) + color compositing (Pillow)
    ├── body_mask_service.py # Clothing mask generation (MediaPipe Pose)
    └── generation_service.py# Stable Diffusion inpainting orchestration (diffusers)
```

### Service Responsibilities — Don't Mix These
- `face_service` → detect faces + classify gender only. No image transformation.
- `background_service` → remove/replace background only. Knows nothing about outfits.
- `body_mask_service` → create torso polygon mask only. Returns a PIL grayscale Image.
- `generation_service` → orchestrate SD inpainting. Calls `body_mask_service` internally.

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/options` | Static options (backgrounds, outfits, genders, `sd_available`) |
| POST | `/api/analyze` | Upload photo → face detect + gender detect. Returns `session_id`. |
| POST | `/api/generate` | `session_id` + options → full pipeline → base64 JPEG result |
| GET | `/api/download/{session_id}` | Return saved result as a downloadable JPEG file |

### Session Pattern
- `/api/analyze` saves normalized image to `backend/uploads/{session_id}.jpg`
- `/api/generate` reads from that file using `session_id`
- `/api/download` reads from `backend/outputs/{session_id}_result.jpg`
- Sessions are file-based — no database, no Redis

### Image Processing Pipeline (in order)
```
Upload → normalize_image (Pillow, max 1024px)
       → detect_face (OpenCV Haar cascades) — reject if no face
       → detect_gender (DeepFace)
       → [optional] generate_outfit_local (SD Inpainting + MediaPipe mask)
       → remove_background (rembg / U2Net)
       → apply_background_color (Pillow composite)
       → 800×800 JPEG output (quality 92)
```

### Error Handling Conventions
- No face → HTTP 422 with `{"code": "NO_FACE_DETECTED", "message": "..."}`
- Invalid file type → HTTP 400
- File > 10MB → HTTP 400
- Session not found → HTTP 404
- Processing failure → HTTP 500 with descriptive `detail`
- SD inpainting failure → **silent fallback** (log warning, continue without outfit change)

### Stable Diffusion Notes
- Model: `runwayml/stable-diffusion-inpainting` (~3.4GB, HuggingFace cache)
- Pipeline is a **singleton** — loaded once per process in `_get_pipeline()`
- Device auto-detected: CUDA (fp16) > MPS/Apple Silicon (fp16) > CPU (fp32)
- `is_sd_available()` checks if `diffusers` is installed — does NOT load the model
- `change_outfit=False` skips SD entirely — pipeline only runs rembg + Pillow

## Frontend Structure

```
src/
├── App.jsx          # 3-step state machine: 'upload' | 'options' | 'result'
└── components/
    ├── UploadStep   # Drag-drop upload → POST /api/analyze
    ├── OptionsStep  # Gender/bg/outfit picker → POST /api/generate
    └── ResultStep   # Display result + download
```

### State Flow
```
App state: { step, analysis, result }

UploadStep:  onDone(analysis)  → sets analysis, step='options'
OptionsStep: onDone(result)    → sets result,   step='result'
ResultStep:  onReset()         → clears all,    step='upload'
```

### Key Frontend Conventions
- All API calls use **axios**, not fetch
- Images are returned as base64 data URIs from the API and used directly in `<img src=...>`
- The download button creates a temporary `<a>` tag pointing to the base64 URI
- `sd_available` comes from the `/api/analyze` response; OptionsStep disables the outfit checkbox if false
- All form submissions to `/api/generate` use `FormData` (not JSON)
- Custom background color is sent as 3 separate form fields: `custom_color_r`, `custom_color_g`, `custom_color_b`

### Tailwind Custom Colors
```js
linkedin: {
  blue:  '#0077B5',  // Primary buttons, active states
  dark:  '#004182',  // Hover states
  light: '#E8F4FD',  // Backgrounds, selected states
}
```

## Coding Patterns to Follow

### Adding a new background preset
Add to `BACKGROUND_COLORS` dict in `background_service.py` — the frontend consumes `/api/options` dynamically, no frontend changes needed.

### Adding a new outfit style
1. Add to `OUTFIT_PROMPTS["male"]` and `OUTFIT_PROMPTS["female"]` in `generation_service.py`
2. Add to `OUTFIT_LABELS` dict in the same file
3. The frontend fetches outfit options from `/api/analyze` response — no frontend changes needed

### Adding a new API route
- Add to `main.py` only
- Use `Form(...)` for multipart/form-data (generation), `File(...)` for uploads
- Always validate `session_id` exists on disk before processing

### Image bytes convention
All service functions accept and return `bytes` (not file paths, not PIL objects).
Exception: `create_clothing_mask()` returns a PIL Image (needed for SD pipeline).

## What NOT to Do
- Do not add external API calls — the entire value prop is 100% local processing
- Do not load the SD pipeline eagerly at import time — use the lazy `_get_pipeline()` singleton
- Do not store user images anywhere other than `uploads/` and `outputs/`
- Do not use `cv2.imshow()` — backend is headless (use `opencv-python-headless`)
- Do not use `npm ci` in CI without a `package-lock.json` committed — use `npm install`

## CI (GitHub Actions)
File: `.github/workflows/ci.yml`
- **Backend job:** Installs lightweight deps only (no torch/diffusers — too heavy for CI). Runs `ruff` lint + `py_compile` syntax check.
- **Frontend job:** Runs `npm install` + `npm run build`. Uploads `dist/` as artifact.
- Heavy ML deps (torch, diffusers, mediapipe) are intentionally excluded from CI.
