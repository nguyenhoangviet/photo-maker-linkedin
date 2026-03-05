"""
Local Stable Diffusion Inpainting for outfit generation.
Uses HuggingFace diffusers — model is downloaded once (~3.4GB) and cached locally.
No external API calls at inference time.
"""
import io
import os
import torch
from PIL import Image
from typing import Optional

from services.body_mask_service import create_clothing_mask

# ---------------------------------------------------------------------------
# Outfit prompt templates
# ---------------------------------------------------------------------------

OUTFIT_PROMPTS = {
    "male": {
        "business_suit": (
            "professional business suit, navy blue blazer, white dress shirt, tie, "
            "LinkedIn headshot, studio portrait, sharp professional look"
        ),
        "business_casual": (
            "smart casual button-up shirt, professional appearance, "
            "LinkedIn profile portrait, clean modern look"
        ),
        "formal_suit": (
            "classic black formal suit, crisp white dress shirt, professional executive, "
            "LinkedIn headshot, studio lighting"
        ),
        "blazer": (
            "charcoal grey blazer, collared shirt, professional business attire, "
            "LinkedIn portrait, polished corporate look"
        ),
    },
    "female": {
        "business_suit": (
            "professional navy blue blazer, white blouse, business attire, "
            "LinkedIn headshot, studio portrait, polished professional look"
        ),
        "business_casual": (
            "elegant smart casual blouse, professional business appearance, "
            "LinkedIn profile portrait, modern professional style"
        ),
        "formal_suit": (
            "black formal blazer suit, executive professional look, "
            "LinkedIn headshot, studio lighting, sophisticated attire"
        ),
        "blazer": (
            "tailored grey blazer, professional business attire, "
            "LinkedIn portrait, clean corporate style"
        ),
    },
}

OUTFIT_LABELS = {
    "business_suit":   "Business Suit",
    "business_casual": "Business Casual",
    "formal_suit":     "Formal Suit",
    "blazer":          "Blazer",
}

NEGATIVE_PROMPT = (
    "cartoon, illustration, anime, bad quality, blurry, distorted face, "
    "extra limbs, deformed, mutation, text, watermark, signature, nsfw, "
    "low resolution, pixelated, overexposed, underexposed"
)

# Singleton pipeline — loaded once per process
_pipeline = None
_pipeline_device = None


def _get_pipeline():
    global _pipeline, _pipeline_device

    if _pipeline is not None:
        return _pipeline, _pipeline_device

    try:
        from diffusers import StableDiffusionInpaintPipeline
    except ImportError:
        raise RuntimeError(
            "diffusers not installed. Run: pip install diffusers transformers accelerate"
        )

    # Determine device
    if torch.cuda.is_available():
        device = "cuda"
        dtype  = torch.float16
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        dtype  = torch.float16
    else:
        device = "cpu"
        dtype  = torch.float32

    print(f"[SD Inpainting] Loading model on {device} ({dtype})...")
    print("[SD Inpainting] First run downloads ~3.4GB — this takes a few minutes.")

    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        "runwayml/stable-diffusion-inpainting",
        torch_dtype=dtype,
        safety_checker=None,          # skip NSFW checker for speed
        requires_safety_checker=False,
    )
    pipe = pipe.to(device)

    # Memory optimisations
    if device == "cpu":
        pipe.enable_attention_slicing()
    elif device == "cuda":
        pipe.enable_attention_slicing()
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass

    _pipeline = pipe
    _pipeline_device = device
    print(f"[SD Inpainting] Model ready on {device}.")
    return _pipeline, _pipeline_device


def _prepare_inputs(image_bytes: bytes, target_size: int = 512):
    """Resize image and mask to SD-compatible dimensions (multiples of 8)."""
    orig = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = orig.size

    # Scale so the longer side = target_size
    scale = target_size / max(w, h)
    new_w = int(w * scale) & ~7   # round down to multiple of 8
    new_h = int(h * scale) & ~7

    resized = orig.resize((new_w, new_h), Image.LANCZOS)
    return resized, (new_w, new_h)


def generate_outfit_local(
    image_bytes: bytes,
    gender: str,
    outfit_style: str,
    strength: float = 0.85,
    guidance_scale: float = 7.5,
    num_steps: int = 30,
) -> Optional[bytes]:
    """
    Run Stable Diffusion inpainting locally to change the outfit.

    Args:
        image_bytes:    Original photo bytes (JPEG/PNG).
        gender:         'male' or 'female'.
        outfit_style:   One of the OUTFIT_PROMPTS keys.
        strength:       How much to change the masked region (0–1).
        guidance_scale: Prompt adherence. Higher = more literal.
        num_steps:      Denoising steps. 20–30 is usually enough.

    Returns:
        JPEG bytes of the result, or None on failure.
    """
    gender_key   = "male" if gender in ("male", "man") else "female"
    outfit_key   = outfit_style if outfit_style in OUTFIT_PROMPTS[gender_key] else "business_suit"
    prompt       = OUTFIT_PROMPTS[gender_key][outfit_key]

    # Build clothing mask
    mask_pil = create_clothing_mask(image_bytes)
    if mask_pil is None:
        print("[SD Inpainting] No mask generated — skipping outfit change.")
        return None

    # Prepare inputs
    image_pil, (tw, th) = _prepare_inputs(image_bytes, target_size=512)
    mask_pil  = mask_pil.resize((tw, th), Image.NEAREST).convert("L")

    # Load pipeline
    try:
        pipe, device = _get_pipeline()
    except RuntimeError as e:
        print(f"[SD Inpainting] Pipeline error: {e}")
        return None

    generator = torch.Generator(device=device).manual_seed(42)

    with torch.inference_mode():
        result = pipe(
            prompt          = prompt,
            negative_prompt = NEGATIVE_PROMPT,
            image           = image_pil,
            mask_image      = mask_pil,
            width           = tw,
            height          = th,
            strength        = strength,
            guidance_scale  = guidance_scale,
            num_inference_steps = num_steps,
            generator       = generator,
        )

    out_image = result.images[0]

    # Return as JPEG bytes
    buf = io.BytesIO()
    out_image.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def get_outfit_options(gender: str) -> list:
    """Return available outfit options for a given gender."""
    gender_key = "male" if gender in ("male", "man") else "female"
    return [
        {"value": key, "label": OUTFIT_LABELS[key]}
        for key in OUTFIT_PROMPTS[gender_key]
    ]


def is_sd_available() -> bool:
    """Check if diffusers is installed (model doesn't need to be loaded yet)."""
    try:
        import diffusers   # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False
