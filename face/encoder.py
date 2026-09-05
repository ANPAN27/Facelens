import logging
import numpy as np
from insightface.app import FaceAnalysis

from config import FACE_DETECTION_MODEL
from face.detector import FaceDetector

logging.getLogger("insightface").setLevel(logging.ERROR)
logging.getLogger("onnxruntime").setLevel(logging.ERROR)


class FaceEncoder:
    def __init__(self):
        self.detector = FaceDetector()

    def encode(self, image: np.ndarray) -> tuple[np.ndarray, dict]:
        faces = self.detector.detect_faces(image)
        if not faces:
            raise ValueError("No face detected for encoding")

        best = max(faces, key=lambda f: f["confidence"])
        if best["embedding"] is None:
            raise ValueError("No embedding produced for detected face")

        return best["embedding"], {
            "bbox": best["bbox"],
            "confidence": best["confidence"],
        }

    def encode_from_detection(self, image: np.ndarray, bbox: list[int]) -> tuple[np.ndarray, dict]:
        face = self.detector.find_by_bbox(image, bbox)
        if face is None:
            raise ValueError("No face detected matching the selected region")

        if face["embedding"] is None:
            raise ValueError("No embedding produced for detected face")

        return face["embedding"], {
            "bbox": face["bbox"],
            "confidence": face["confidence"],
        }