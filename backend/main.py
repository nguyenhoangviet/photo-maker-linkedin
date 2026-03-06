import io
import os
import base64
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image

from services.face_service import detect_face, detect_gender
from services.background_service import (
    remove_background,
    apply_background_color,
    BACKGROUND_COLORS,
)
from services.generation_service import (
    generate_outfit_local,
    get_outfit_options,
    is_sd_available,
)

app = FastAPI(title="LinkedIn Photo Maker", version="2.0.0")

# ALLOWED_ORIGINS env var: comma-separated list of allowed frontend URLs.
# Defaults to local dev origins.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


def image_to_base64(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"


def normalize_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Resize large images to avoid slow processing."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "LinkedIn Photo Maker API",
        "sd_available": is_sd_available(),
    }


@app.get("/api/options")
async def get_options():
    """Return available backgrounds, outfit options, and capability flags."""
    return {
        "backgrounds": [
            {"value": key, "label": key.replace("_", " ").title(), "color": f"rgb{str(rgb)}"}
            for key, rgb in BACKGROUND_COLORS.items()
        ],
        "outfits": {
            "male":   get_outfit_options("male"),
            "female": get_outfit_options("female"),
        },
        "genders": [
            {"value": "male",   "label": "Male"},
            {"value": "female", "label": "Female"},
        ],
        "sd_available": is_sd_available(),
    }


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Step 1: Upload and analyze the image.
    Detects face presence and gender.
    Returns analysis results + preview image.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Please upload JPEG, PNG, or WebP.",
        )

    image_bytes = await file.read()

    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        normalized = normalize_image(image_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not process image. Please upload a valid photo.")

    # Face detection — reject if no human face found
    face_result = detect_face(normalized)
    if not face_result["has_face"]:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "NO_FACE_DETECTED",
                "message": face_result.get(
                    "message",
                    "No human face detected. Please upload a photo with a clearly visible face.",
                ),
            },
        )

    # Gender detection (local DeepFace)
    gender_result = detect_gender(normalized)

    # Persist for later generation call
    session_id = str(uuid.uuid4())
    (UPLOAD_DIR / f"{session_id}.jpg").write_bytes(normalized)

    return {
        "session_id":        session_id,
        "face_count":        face_result["face_count"],
        "gender":            gender_result["gender"],
        "gender_confidence": gender_result["confidence"],
        "preview":           image_to_base64(normalized),
        "image_b64":         image_to_base64(normalized),
        "sd_available":      is_sd_available(),
        "outfits": {
            "male":   get_outfit_options("male"),
            "female": get_outfit_options("female"),
        },
    }


@app.post("/api/generate")
async def generate_photo(
    gender:           str           = Form(...),
    background_color: str           = Form("classic_gray"),
    custom_color_r:   Optional[int] = Form(None),
    custom_color_g:   Optional[int] = Form(None),
    custom_color_b:   Optional[int] = Form(None),
    outfit_style:     str           = Form("business_suit"),
    change_outfit:    bool          = Form(False),
    # Accept either session_id (local) or image_b64 (Vercel stateless)
    session_id:       Optional[str] = Form(None),
    image_b64:        Optional[str] = Form(None),
):
    """
    Generate the professional LinkedIn photo.
    Accepts either session_id (local file) or image_b64 (stateless/Vercel).
    Pipeline: SD inpainting (opt.) → rembg → solid background → 800×800 JPEG
    """
    if gender not in ("male", "female"):
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'.")

    if background_color not in BACKGROUND_COLORS and not all(
        v is not None for v in [custom_color_r, custom_color_g, custom_color_b]
    ):
        background_color = "classic_gray"

    # Resolve image bytes from session file or base64 payload
    if image_b64:
        try:
            import base64 as _b64
            data = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64
            image_bytes = _b64.b64decode(data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image_b64 data.")
    elif session_id:
        session_path = UPLOAD_DIR / f"{session_id}.jpg"
        if not session_path.exists():
            raise HTTPException(status_code=404, detail="Session expired. Please upload again.")
        image_bytes = session_path.read_bytes()
    else:
        raise HTTPException(status_code=400, detail="Provide either session_id or image_b64.")
    outfit_applied = False

    # --- Step 1: outfit change via local SD inpainting (optional) ---
    if change_outfit and is_sd_available():
        try:
            outfit_result = generate_outfit_local(
                image_bytes=image_bytes,
                gender=gender,
                outfit_style=outfit_style,
            )
            if outfit_result:
                image_bytes   = outfit_result
                outfit_applied = True
        except Exception as e:
            print(f"[generate] Outfit generation failed, continuing without: {e}")

    # --- Step 2: remove background ---
    try:
        fg_bytes = remove_background(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Background removal failed: {e}")

    # --- Step 3: apply background color ---
    custom_color = None
    if all(v is not None for v in [custom_color_r, custom_color_g, custom_color_b]):
        custom_color = (custom_color_r, custom_color_g, custom_color_b)

    try:
        result_bytes = apply_background_color(
            foreground_bytes=fg_bytes,
            color_name=background_color,
            custom_color=custom_color,
            output_size=(800, 800),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Background application failed: {e}")

    # Persist result
    (OUTPUT_DIR / f"{session_id}_result.jpg").write_bytes(result_bytes)

    return {
        "success":       True,
        "result":        image_to_base64(result_bytes),
        "outfit_applied": outfit_applied,
        "download_url":  f"/api/download/{session_id}",
    }


@app.get("/api/download/{session_id}")
async def download_photo(session_id: str):
    """Download the generated photo as a JPEG file."""
    output_path = OUTPUT_DIR / f"{session_id}_result.jpg"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Result not found.")

    return Response(
        content=output_path.read_bytes(),
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"attachment; filename=linkedin_photo_{session_id[:8]}.jpg"
        },
    )
