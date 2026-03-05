"""
Body mask generation using MediaPipe Pose.
Creates a torso/clothing mask for use with Stable Diffusion inpainting.
"""
import cv2
import numpy as np
from PIL import Image
import io
from typing import Optional


def _image_bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _cv2_to_pil(img: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def create_clothing_mask(image_bytes: bytes) -> Optional[Image.Image]:
    """
    Use MediaPipe Pose to detect body landmarks and create a torso mask
    suitable for Stable Diffusion inpainting (outfit region).

    Returns a grayscale PIL image (white = inpaint region, black = keep).
    Returns None if pose not detected.
    """
    try:
        import mediapipe as mp
    except ImportError:
        return _fallback_torso_mask(image_bytes)

    mp_pose = mp.solutions.pose

    img_cv = _image_bytes_to_cv2(image_bytes)
    h, w = img_cv.shape[:2]
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

    with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=True,
        min_detection_confidence=0.4,
    ) as pose:
        results = pose.process(img_rgb)

    if not results.pose_landmarks:
        return _fallback_torso_mask(image_bytes)

    lm = results.pose_landmarks.landmark
    LM = mp_pose.PoseLandmark

    def pt(idx):
        p = lm[idx]
        return int(p.x * w), int(p.y * h)

    # Key landmarks for torso/clothing area
    l_shoulder  = pt(LM.LEFT_SHOULDER)
    r_shoulder  = pt(LM.RIGHT_SHOULDER)
    l_hip       = pt(LM.LEFT_HIP)
    r_hip       = pt(LM.RIGHT_HIP)
    l_elbow     = pt(LM.LEFT_ELBOW)
    r_elbow     = pt(LM.RIGHT_ELBOW)

    # Build torso polygon with generous padding
    shoulder_w   = abs(r_shoulder[0] - l_shoulder[0])
    h_pad_side   = int(shoulder_w * 0.25)
    extra_up     = int(h * 0.05)   # extra above shoulders
    extra_down   = int(h * 0.04)   # extra below hips

    # Upper boundary: slightly above shoulders / just below chin
    top_y = max(0, min(l_shoulder[1], r_shoulder[1]) - extra_up)

    # Include arms up to elbows
    l_arm_x = min(l_shoulder[0], l_elbow[0]) - h_pad_side
    r_arm_x = max(r_shoulder[0], r_elbow[0]) + h_pad_side

    polygon = np.array([
        [r_arm_x,               top_y],
        [l_arm_x,               top_y],
        [l_shoulder[0] - h_pad_side, l_shoulder[1]],
        [l_hip[0] - h_pad_side,      l_hip[1] + extra_down],
        [r_hip[0] + h_pad_side,      r_hip[1] + extra_down],
        [r_shoulder[0] + h_pad_side, r_shoulder[1]],
    ], dtype=np.int32)

    # Clamp to image bounds
    polygon[:, 0] = np.clip(polygon[:, 0], 0, w - 1)
    polygon[:, 1] = np.clip(polygon[:, 1], 0, h - 1)

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)

    # Soft blur edges for smoother inpainting
    mask = cv2.GaussianBlur(mask, (21, 21), 0)
    _, mask = cv2.threshold(mask, 64, 255, cv2.THRESH_BINARY)

    return Image.fromarray(mask)


def _fallback_torso_mask(image_bytes: bytes) -> Image.Image:
    """
    Heuristic fallback when MediaPipe pose detection fails.
    Assumes standard portrait: face ~top 30%, torso 30–80% of height.
    """
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size

    mask = Image.new("L", (w, h), 0)
    import PIL.ImageDraw as ImageDraw
    draw = ImageDraw.Draw(mask)

    # Rough torso region: x 10–90%, y 25–80%
    top    = int(h * 0.25)
    bottom = int(h * 0.80)
    left   = int(w * 0.10)
    right  = int(w * 0.90)
    draw.rectangle([left, top, right, bottom], fill=255)

    return mask
