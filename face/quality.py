import cv2
import numpy as np


def compute_face_quality(face_img: np.ndarray) -> dict:
    if face_img is None or face_img.size == 0:
        return {"score": 0.0, "usable": False, "reason": "Empty face image"}

    h, w = face_img.shape[:2]
    if h < 32 or w < 32:
        return {"score": 0.0, "usable": False, "reason": f"Face too small: {w}x{h}"}

    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY) if len(face_img.shape) == 3 else face_img

    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = np.mean(gray)
    contrast = np.std(gray)

    score = 0.0
    reasons = []

    if blur_score < 50:
        reasons.append(f"Blurry (var={blur_score:.1f})")
    else:
        score += 0.4

    if brightness < 30 or brightness > 225:
        reasons.append(f"Bad brightness ({brightness:.0f})")
    else:
        score += 0.3

    if contrast < 20:
        reasons.append(f"Low contrast ({contrast:.0f})")
    else:
        score += 0.3

    usable = score >= 0.3 and h >= 48 and w >= 48
    reason = "; ".join(reasons) if reasons else "OK"

    return {"score": score, "usable": usable, "reason": reason}
