"""
Vercel-compatible FastAPI backend.
Lightweight: OpenCV face detection + rembg background removal only.
No deepface/torch/diffusers — fits within Vercel's 250MB function limit.
Stateless: image is base64-encoded in request body, no session files.
"""
import os
# Must be set before rembg import so the model downloads to /tmp (writable on Vercel)
os.environ.setdefault("U2NET_HOME", "/tmp/.u2net")

import io
import base64
import uuid
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from PIL import Image, ImageEnhance

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="LinkedIn Photo Maker API", version="3.0.0")

_raw = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://*.vercel.app",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Vercel preview URLs vary; tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

BACKGROUND_COLORS = {
    "classic_gray":   (240, 240, 240),
    "corporate_blue": (31,  78,  121),
    "navy":           (0,   32,   63),
    "light_blue":     (173, 216, 230),
    "white":          (255, 255, 255),
    "off_white":      (245, 245, 245),
    "slate":          (112, 128, 144),
    "dark_gray":      (64,   64,  64),
    "teal":           (0,   128, 128),
    "forest_green":   (34,   85,  34),
}

OUTFIT_OPTIONS = [
    {"value": "business_suit",   "label": "Business Suit"},
    {"value": "business_casual", "label": "Business Casual"},
    {"value": "formal_suit",     "label": "Formal Suit"},
    {"value": "blazer",          "label": "Blazer"},
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def img_to_b64(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"


def b64_to_bytes(data_uri: str) -> bytes:
    """Accept either a data URI or raw base64."""
    if data_uri.startswith("data:"):
        data_uri = data_uri.split(",", 1)[1]
    return base64.b64decode(data_uri)


def normalize(image_bytes: bytes, max_size: int = 1024) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_size:
        r = max_size / max(w, h)
        img = img.resize((int(w * r), int(h * r)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def detect_face(image_bytes: bytes) -> dict:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"has_face": False, "face_count": 0}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50))

    if len(faces) == 0:
        profile = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_profileface.xml"
        )
        faces = profile.detectMultiScale(gray, 1.1, 5, minSize=(50, 50))

    return {"has_face": len(faces) > 0, "face_count": int(len(faces))}


def remove_bg(image_bytes: bytes) -> bytes:
    from rembg import remove as rembg_remove
    return rembg_remove(image_bytes)


def apply_bg_color(
    fg_bytes: bytes,
    color_name: str = "classic_gray",
    custom_color: Optional[tuple] = None,
    size: int = 800,
) -> bytes:
    fg = Image.open(io.BytesIO(fg_bytes)).convert("RGBA")
    rgb = custom_color if custom_color else BACKGROUND_COLORS.get(color_name, (240, 240, 240))
    bg = Image.new("RGBA", fg.size, rgb + (255,))
    out = Image.alpha_composite(bg, fg).resize((size, size), Image.LANCZOS).convert("RGB")
    out = ImageEnhance.Sharpness(out).enhance(1.2)
    out = ImageEnhance.Contrast(out).enhance(1.05)
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api")
@app.get("/api/")
async def root():
    return {"status": "ok", "service": "LinkedIn Photo Maker API", "version": "3.0.0"}


@app.get("/api/options")
async def get_options():
    return {
        "backgrounds": [
            {"value": k, "label": k.replace("_", " ").title(), "color": f"rgb{v}"}
            for k, v in BACKGROUND_COLORS.items()
        ],
        "outfits": {"male": OUTFIT_OPTIONS, "female": OUTFIT_OPTIONS},
        "genders": [{"value": "male", "label": "Male"}, {"value": "female", "label": "Female"}],
        "sd_available": False,   # outfit AI not available on Vercel
    }


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported type: {file.content_type}")

    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large. Max 10MB.")
    if not raw:
        raise HTTPException(400, "Empty file.")

    try:
        normalized = normalize(raw)
    except Exception:
        raise HTTPException(400, "Could not read image.")

    result = detect_face(normalized)
    if not result["has_face"]:
        raise HTTPException(
            422,
            detail={
                "code": "NO_FACE_DETECTED",
                "message": "No human face detected. Please upload a photo with a clearly visible face.",
            },
        )

    return {
        "session_id":        str(uuid.uuid4()),   # unused but keeps frontend compat
        "face_count":        result["face_count"],
        "gender":            "unknown",            # no deepface on Vercel — user selects
        "gender_confidence": 0,
        "preview":           img_to_b64(normalized),
        "image_b64":         img_to_b64(normalized),   # sent back for stateless generate
        "sd_available":      False,
        "outfits":           {"male": OUTFIT_OPTIONS, "female": OUTFIT_OPTIONS},
    }


@app.post("/api/generate")
async def generate(
    image_b64:      str           = Form(...),
    gender:         str           = Form("male"),
    background_color: str         = Form("classic_gray"),
    custom_color_r: Optional[int] = Form(None),
    custom_color_g: Optional[int] = Form(None),
    custom_color_b: Optional[int] = Form(None),
    outfit_style:   str           = Form("business_suit"),
    change_outfit:  bool          = Form(False),
):
    if gender not in ("male", "female"):
        gender = "male"

    try:
        image_bytes = normalize(b64_to_bytes(image_b64))
    except Exception:
        raise HTTPException(400, "Invalid image data.")

    # Background removal
    try:
        fg = remove_bg(image_bytes)
    except Exception as e:
        raise HTTPException(500, f"Background removal failed: {e}")

    # Apply colour
    custom = None
    if all(v is not None for v in [custom_color_r, custom_color_g, custom_color_b]):
        custom = (custom_color_r, custom_color_g, custom_color_b)

    try:
        result = apply_bg_color(fg, background_color, custom)
    except Exception as e:
        raise HTTPException(500, f"Background apply failed: {e}")

    return {
        "success":        True,
        "result":         img_to_b64(result),
        "outfit_applied": False,
        "download_url":   None,
    }


# ---------------------------------------------------------------------------
# Vercel entry point
# ---------------------------------------------------------------------------
handler = Mangum(app, lifespan="off")
