import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def l2_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def compare_faces(embedding_a: np.ndarray, embedding_b: np.ndarray) -> dict:
    sim = cosine_similarity(embedding_a, embedding_b)
    dist = l2_distance(embedding_a, embedding_b)
    return {"similarity": sim, "distance": dist}
