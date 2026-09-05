import hashlib
import json
from typing import Any


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_string(s: str) -> str:
    return sha256_hex(s.encode("utf-8"))


def sha256_json(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return sha256_string(canonical)


def compute_record_hash(input_image_hash: str, candidate_hash: str, similarity: float, result: str, timestamp: int) -> str:
    record = {
        "input_image_hash": input_image_hash,
        "candidate_hash": candidate_hash,
        "similarity": similarity,
        "result": result,
        "timestamp": timestamp,
    }
    return sha256_json(record)
