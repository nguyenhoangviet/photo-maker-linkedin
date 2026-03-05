import cv2
import numpy as np
from deepface import DeepFace
from PIL import Image
import io
import base64
from typing import Optional


def decode_image(image_bytes: bytes) -> np.ndarray:
    """Convert bytes to OpenCV image."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def detect_face(image_bytes: bytes) -> dict:
    """
    Detect if a human face is present in the image.
    Returns detection result with face count and bounding boxes.
    """
    img = decode_image(image_bytes)
    if img is None:
        return {"has_face": False, "error": "Could not decode image"}

    # Use OpenCV face detection as fast first pass
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))

    if len(faces) == 0:
        # Try profile face detection
        profile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_profileface.xml"
        )
        faces = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))

    if len(faces) == 0:
        return {
            "has_face": False,
            "face_count": 0,
            "message": "No human face detected. Please upload a photo with a clearly visible face.",
        }

    return {
        "has_face": True,
        "face_count": len(faces),
        "faces": [
            {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            for (x, y, w, h) in faces
        ],
    }


def detect_gender(image_bytes: bytes) -> dict:
    """
    Detect gender from face in the image using DeepFace.
    Returns detected gender and confidence.
    """
    img = decode_image(image_bytes)
    if img is None:
        return {"gender": "unknown", "confidence": 0}

    try:
        # Save to temp buffer for DeepFace
        _, buffer = cv2.imencode(".jpg", img)
        img_array = cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_COLOR)

        result = DeepFace.analyze(
            img_path=img_array,
            actions=["gender"],
            enforce_detection=False,
            silent=True,
        )

        if isinstance(result, list):
            result = result[0]

        gender_data = result.get("gender", {})

        if isinstance(gender_data, dict):
            # gender_data is {"Man": score, "Woman": score}
            detected = max(gender_data, key=gender_data.get)
            confidence = gender_data[detected]
            gender = "male" if detected == "Man" else "female"
        else:
            gender = "male" if str(gender_data).lower() == "man" else "female"
            confidence = 0.7

        return {
            "gender": gender,
            "confidence": round(float(confidence), 2),
            "raw": gender_data if isinstance(gender_data, dict) else str(gender_data),
        }

    except Exception as e:
        # Default to unknown if analysis fails
        return {"gender": "unknown", "confidence": 0, "error": str(e)}
