from rembg import remove
from PIL import Image, ImageFilter, ImageEnhance
import io
import numpy as np


# Professional LinkedIn background colors
BACKGROUND_COLORS = {
    "classic_gray": (240, 240, 240),
    "corporate_blue": (31, 78, 121),
    "navy": (0, 32, 63),
    "light_blue": (173, 216, 230),
    "white": (255, 255, 255),
    "off_white": (245, 245, 245),
    "slate": (112, 128, 144),
    "dark_gray": (64, 64, 64),
    "teal": (0, 128, 128),
    "forest_green": (34, 85, 34),
}


def remove_background(image_bytes: bytes) -> bytes:
    """Remove background from image using rembg (U2Net model)."""
    output_bytes = remove(image_bytes)
    return output_bytes


def apply_background_color(
    foreground_bytes: bytes,
    color_name: str = "classic_gray",
    custom_color: tuple = None,
    output_size: tuple = (800, 800),
) -> bytes:
    """
    Composite foreground (person with transparent bg) onto a solid color background.
    Returns JPEG bytes.
    """
    # Load foreground (RGBA)
    fg_image = Image.open(io.BytesIO(foreground_bytes)).convert("RGBA")

    # Determine background color
    if custom_color:
        bg_color = tuple(custom_color) + (255,)
    else:
        rgb = BACKGROUND_COLORS.get(color_name, BACKGROUND_COLORS["classic_gray"])
        bg_color = rgb + (255,)

    # Create background
    bg = Image.new("RGBA", fg_image.size, bg_color)

    # Composite
    composite = Image.alpha_composite(bg, fg_image)

    # Resize to LinkedIn-optimal square
    composite = composite.resize(output_size, Image.LANCZOS)

    # Enhance for professional look
    enhancer = ImageEnhance.Sharpness(composite)
    composite = enhancer.enhance(1.2)

    enhancer = ImageEnhance.Contrast(composite)
    composite = enhancer.enhance(1.05)

    # Convert to RGB JPEG
    final = composite.convert("RGB")
    output = io.BytesIO()
    final.save(output, format="JPEG", quality=92)
    return output.getvalue()


def crop_to_portrait(image_bytes: bytes) -> bytes:
    """
    Crop image to a portrait/headshot ratio (4:5) centered on the face area.
    """
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    # Target 4:5 ratio
    target_ratio = 4 / 5
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Too wide, crop sides
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    elif current_ratio < target_ratio:
        # Too tall, crop bottom (keep head at top)
        new_h = int(w / target_ratio)
        img = img.crop((0, 0, w, new_h))

    output = io.BytesIO()
    img_format = "PNG" if img.mode == "RGBA" else "JPEG"
    img.save(output, format=img_format)
    return output.getvalue()
