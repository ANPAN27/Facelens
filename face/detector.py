import logging
import numpy as np
from insightface.app import FaceAnalysis

from config import FACE_DETECTION_MODEL

logging.getLogger("insightface").setLevel(logging.ERROR)
logging.getLogger("onnxruntime").setLevel(logging.ERROR)


class FaceDetector:
    def __init__(self):
        self.app = FaceAnalysis(name=FACE_DETECTION_MODEL, providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=0, det_size=(640, 640))

    def detect_faces(self, image: np.ndarray) -> list[dict]:
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