import os
import tempfile

import cv2
import numpy as np

from candidates.downloader import download_image
from face.detector import FaceDetector
from face.quality import compute_face_quality
from config import MAX_CANDIDATE_IMAGES


class CandidateProcessor:
    def __init__(self):
        self.detector = FaceDetector()

    def process(self, candidates: list[dict]) -> list[dict]:
        processed = []
        temp_dir = tempfile.mkdtemp(prefix="facelens_")

        count = 0
        for c in candidates:
            if count >= MAX_CANDIDATE_IMAGES:
                break

            image_url = c.get("image_url", "")
            if not image_url:
                processed.append({**c, "face_detected": False, "faces": [], "local_path": None})
                continue

            local_path = download_image(image_url, temp_dir, count)
            if not local_path:
                processed.append({**c, "face_detected": False, "faces": [], "local_path": None})
                continue

            try:
                img = cv2.imread(local_path)
                if img is None:
                    processed.append({**c, "face_detected": False, "faces": [], "local_path": local_path})
                    count += 1
                    continue

                faces = self.detector.detect_faces(img)
                face_data = []
                for f in faces:
                    x1, y1, x2, y2 = f["bbox"]
                    face_crop = img[max(0, y1):y2, max(0, x1):x2]
                    quality = compute_face_quality(face_crop)

                    embedding = f.get("embedding") if quality["usable"] else None
                    face_data.append({
                        "bbox": f["bbox"],
                        "confidence": f["confidence"],
                        "quality": quality,
                        "embedding": embedding,
                    })

                processed.append({
                    **c,
                    "face_detected": len(face_data) > 0,
                    "faces": face_data,
                    "local_path": local_path,
                })
            except Exception:
                processed.append({**c, "face_detected": False, "faces": [], "local_path": local_path})

            count += 1

        return processed
