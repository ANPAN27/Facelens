import contextlib
import io
import logging
import warnings

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from config import FACE_DETECTION_MODEL


class _IgnoreInsightface(logging.Filter):
    def filter(self, record):
        return not (
            record.name.startswith("insightface")
            or record.name.startswith("onnxruntime")
        )


logging.getLogger().addFilter(_IgnoreInsightface())
warnings.filterwarnings("ignore", category=FutureWarning, module="insightface.utils")
_SILENCE = contextlib.redirect_stdout(io.StringIO())


def crop_face(image: np.ndarray, bbox: list[int], scale: float = 1.5) -> np.ndarray:
    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    face_w, face_h = x2 - x1, y2 - y1
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    pad_w, pad_h = face_w * (scale - 1) / 2.0, face_h * (scale - 1) / 2.0
    n_x1 = max(0, int(cx - pad_w - face_w / 2.0))
    n_y1 = max(0, int(cy - pad_h - face_h / 2.0))
    n_x2 = min(w, int(cx + pad_w + face_w / 2.0))
    n_y2 = min(h, int(cy + pad_h + face_h / 2.0))
    if n_x2 - n_x1 < 24 or n_y2 - n_y1 < 24:
        n_x1, n_y1, n_x2, n_y2 = x1, y1, x2, y2
    return image[n_y1:n_y2, n_x1:n_x2]


def crop_face_only(
    image: np.ndarray,
    bbox: list[int],
    landmarks: list[list[float]] | None = None,
    scale: float = 1.08,
    mask_background: bool = True,
) -> np.ndarray:
    """Tight face crop with everything outside the face blacked out."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    bw, bh = x2 - x1, y2 - y1
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    ext_w, ext_h = bw * scale, bh * scale
    n_x1 = max(0, int(cx - ext_w / 2.0))
    n_y1 = max(0, int(cy - ext_h / 2.0))
    n_x2 = min(w, int(cx + ext_w / 2.0))
    n_y2 = min(h, int(cy + ext_h / 2.0))
    crop = image[n_y1:n_y2, n_x1:n_x2].copy()
    if crop.size == 0:
        return crop
    if not mask_background:
        return crop

    ch, cw = crop.shape[:2]
    mask = np.zeros((ch, cw), dtype=np.uint8)
    if landmarks is not None and len(landmarks) >= 3:
        pts = np.asarray(landmarks, dtype=float)
        eye = np.mean(pts[:2], axis=0)
        nose = pts[2]
        mcx = eye[0] - n_x1
        mcy = (eye[1] + nose[1]) / 2.0 - n_y1
        rx = max(float(np.linalg.norm(pts[1] - pts[0])) * 0.9, bw * 0.52)
        ry = max(float(np.linalg.norm(pts[4] - pts[2])) * 2.0, bh * 0.68)
    else:
        mcx, mcy = cw / 2.0, ch / 2.0
        rx, ry = bw * 0.55, bh * 0.72
    ry = min(ry, ch * 0.96)
    cv2.ellipse(mask, (int(mcx), int(mcy)), (max(8, int(rx)), max(8, int(ry))), 0, 0, 360, 255, thickness=-1)
    crop[mask == 0] = 0
    return crop


class FaceDetector:
    def __init__(self):
        with _SILENCE:
            self.app = FaceAnalysis(name=FACE_DETECTION_MODEL, providers=["CPUExecutionProvider"])
            self.app.prepare(ctx_id=0, det_size=(640, 640))

    def detect_faces(self, image: np.ndarray) -> list[dict]:
        faces = self._run(image, (640, 640))
        if not faces:
            faces = self._run(image, (0, 0))
        return faces

    def _run(self, image: np.ndarray, det_size: tuple) -> list[dict]:
        with _SILENCE:
            self.app.prepare(ctx_id=0, det_size=det_size)
            faces = self.app.get(image)
        results = []
        for face in faces:
            bbox = face.bbox.astype(int)
            embedding = face.embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            results.append({
                "bbox": bbox.tolist(),
                "confidence": float(face.det_score),
                "landmarks": face.kps.tolist() if face.kps is not None else None,
                "embedding": embedding,
            })
        return results

    def select_face(self, faces: list[dict], index: int = 0) -> dict:
        if not faces:
            raise ValueError("No faces to select")
        if index < 0 or index >= len(faces):
            raise ValueError(f"Invalid face index: {index}")
        return faces[index]

    def find_by_bbox(self, image: np.ndarray, bbox: list[int]) -> dict | None:
        target_x1, target_y1, target_x2, target_y2 = bbox
        target_area = max(1, (target_x2 - target_x1) * (target_y2 - target_y1))
        best = None
        best_iou = -1.0
        for face in self.detect_faces(image):
            x1, y1, x2, y2 = face["bbox"]
            inter_x1 = max(x1, target_x1)
            inter_y1 = max(y1, target_y1)
            inter_x2 = min(x2, target_x2)
            inter_y2 = min(y2, target_y2)
            inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
            union_area = max(1, (x2 - x1) * (y2 - y1) + target_area - inter_area)
            iou = inter_area / union_area
            if iou > best_iou:
                best_iou = iou
                best = face
        return best