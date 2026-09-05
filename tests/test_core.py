import os
import sys
import json
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.hashing import sha256_hex, sha256_string, sha256_json, compute_record_hash
from utils.image import validate_image, compute_file_hash
from face.quality import compute_face_quality
from face.matcher import cosine_similarity, l2_distance, compare_faces
from candidates.extractor import extract_candidates
from ranking.ranker import classify_match, compute_source_score, rank_candidates
from verification.verifier import VerificationResult


class TestHashing:
    def test_sha256_hex(self):
        result = sha256_hex(b"hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert result == expected

    def test_sha256_string(self):
        result = sha256_string("hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert result == expected

    def test_sha256_json_deterministic(self):
        obj = {"b": 2, "a": 1}
        h1 = sha256_json(obj)
        h2 = sha256_json(obj)
        assert h1 == h2

    def test_sha256_json_sorted_keys(self):
        h1 = sha256_json({"a": 1, "b": 2})
        h2 = sha256_json({"b": 2, "a": 1})
        assert h1 == h2

    def test_compute_record_hash(self):
        h = compute_record_hash("abc", "def", 0.95, "HIGH_SIMILARITY", 1000000)
        assert isinstance(h, str)
        assert len(h) == 64


class TestImageUtils:
    def test_validate_nonexistent(self):
        ok, msg = validate_image("/nonexistent/file.jpg")
        assert not ok
        assert "not found" in msg

    def test_validate_bad_format(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not an image")
            path = f.name
        try:
            ok, msg = validate_image(path)
            assert not ok
            assert "Unsupported" in msg
        finally:
            os.unlink(path)

    def test_validate_good_jpg(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            cv2.imwrite(f.name, img)
            path = f.name
        try:
            ok, msg = validate_image(path)
            assert ok
        finally:
            os.unlink(path)

    def test_compute_file_hash(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test data")
            path = f.name
        try:
            h = compute_file_hash(path)
            expected = hashlib.sha256(b"test data").hexdigest()
            assert h == expected
        finally:
            os.unlink(path)


class TestFaceQuality:
    def test_empty_image(self):
        result = compute_face_quality(np.array([]))
        assert not result["usable"]

    def test_tiny_image(self):
        tiny = np.zeros((10, 10, 3), dtype=np.uint8)
        result = compute_face_quality(tiny)
        assert not result["usable"]

    def test_good_image(self):
        img = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
        result = compute_face_quality(img)
        assert result["score"] > 0


class TestFaceMatcher:
    def test_identical_vectors(self):
        v = np.array([1.0, 0.0, 0.0])
        sim = cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        sim = cosine_similarity(a, b)
        assert abs(sim) < 1e-6

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        sim = cosine_similarity(a, b)
        assert abs(sim + 1.0) < 1e-6

    def test_zero_vector(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        sim = cosine_similarity(a, b)
        assert sim == 0.0

    def test_l2_distance(self):
        a = np.array([0.0, 0.0])
        b = np.array([3.0, 4.0])
        dist = l2_distance(a, b)
        assert abs(dist - 5.0) < 1e-6

    def test_compare_faces(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.9, 0.1, 0.0])
        result = compare_faces(a, b)
        assert "similarity" in result
        assert "distance" in result
        assert result["similarity"] > 0.8


class TestCandidateExtractor:
    def test_extracts_valid(self):
        results = [
            {"url": "https://example.com", "title": "Test", "image_url": "https://example.com/img.jpg", "platform": "Website"},
            {"error": "failed"},
            {"url": "", "title": "Empty"},
        ]
        candidates = extract_candidates(results)
        assert len(candidates) == 1
        assert candidates[0]["url"] == "https://example.com"

    def test_empty_results(self):
        assert extract_candidates([]) == []


class TestRanker:
    def test_classify_high(self):
        assert classify_match(0.95) == "HIGH"
        assert classify_match(0.90) == "HIGH"

    def test_classify_medium(self):
        assert classify_match(0.85) == "MEDIUM"
        assert classify_match(0.80) == "MEDIUM"

    def test_classify_low(self):
        assert classify_match(0.50) == "LOW"

    def test_source_score_social(self):
        assert compute_source_score("Instagram") == 1.0
        assert compute_source_score("Facebook") == 1.0

    def test_source_score_news(self):
        assert compute_source_score("News") == 0.7

    def test_rank_candidates(self):
        emb = np.array([1.0, 0.0, 0.0])
        candidates = [
            {
                "face_detected": True,
                "faces": [{"embedding": np.array([0.9, 0.1, 0.0])}],
                "platform": "Instagram",
                "url": "https://instagram.com/test",
            },
            {
                "face_detected": True,
                "faces": [{"embedding": np.array([0.5, 0.5, 0.0])}],
                "platform": "Website",
                "url": "https://example.com",
            },
        ]
        ranked = rank_candidates(emb, candidates)
        assert len(ranked) == 2
        assert ranked[0]["face_similarity"] >= ranked[1]["face_similarity"]


class TestVerificationResult:
    def test_creates_hash(self):
        v = VerificationResult("abc123", [])
        assert len(v.record_hash) == 64
        assert v.timestamp > 0

    def test_to_dict(self):
        v = VerificationResult("abc123", [
            {"platform": "Instagram", "url": "https://ig.com", "face_similarity": 0.95, "classification": "HIGH"}
        ])
        d = v.to_dict()
        assert d["input_image_hash"] == "abc123"
        assert len(d["results"]) == 1
        assert d["results"][0]["face_similarity"] == 0.95

    def test_set_blockchain(self):
        v = VerificationResult("abc", [])
        v.set_blockchain("sepolia", "0xabc")
        assert v.blockchain["network"] == "sepolia"
        assert v.blockchain["transaction"] == "0xabc"
