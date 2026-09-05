import hashlib
from pathlib import Path
from PIL import Image
import cv2
import numpy as np

from config import SUPPORTED_FORMATS, MAX_IMAGE_SIZE_MB


def validate_image(path: str) -> tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        return False, f"File not found: {path}"
    if p.suffix.lower() not in SUPPORTED_FORMATS:
        return False, f"Unsupported format: {p.suffix}. Use {SUPPORTED_FORMATS}"
    if p.stat().st_size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        return False, f"File too large: {p.stat().st_size / 1024 / 1024:.1f}MB > {MAX_IMAGE_SIZE_MB}MB"
    try:
        img = Image.open(p)
        img.verify()
    except Exception as e:
        return False, f"Cannot read image: {e}"
    return True, "OK"


def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Failed to load image: {path}")
    return img


def resize_for_display(img: np.ndarray, max_width: int = 800) -> np.ndarray:
    h, w = img.shape[:2]
    if w > max_width:
        ratio = max_width / w
        img = cv2.resize(img, (max_width, int(h * ratio)))
    return img


def compute_file_hash(path: str) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def pil_to_cv2(pil_img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_img: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB))
