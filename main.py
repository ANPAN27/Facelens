#!/usr/bin/env python3
import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.prompt import Prompt, IntPrompt
from rich.console import Console

from config import RESULTS_DIR, SIMILARITY_THRESHOLD_HIGH, SIMILARITY_THRESHOLD_MEDIUM
from utils.image import validate_image, load_image, compute_file_hash
from utils.logger import (
    banner, step_header, step_done, step_fail, info, warn, error,
    match_table, blockchain_result, completion_banner, console,
)
from face.detector import FaceDetector
from face.encoder import FaceEncoder
from face.quality import compute_face_quality
from search.reverse_search import search_image
from candidates.extractor import extract_candidates
from candidates.processor import CandidateProcessor
from ranking.ranker import rank_candidates
from verification.verifier import VerificationResult
from blockchain.client import BlockchainClient

TOTAL_STEPS = 8


def run_search(image_path: str, max_results: int = 20):
    banner()

    console.print(f"[bold]Input Image:[/bold] {image_path}")
    console.print()

    # Step 1: Load image
    step_header(1, TOTAL_STEPS, "Loading image")
    valid, msg = validate_image(image_path)
    if not valid:
        step_fail("Loading image", msg)
        sys.exit(1)
    image = load_image(image_path)
    step_done(f"Image loaded ({image.shape[1]}x{image.shape[0]})")
    console.print()

    # Step 2: Face detection
    step_header(2, TOTAL_STEPS, "Detecting faces")
    detector = FaceDetector()
    faces = detector.detect_faces(image)
    if not faces:
        step_fail("Detecting faces", "No usable face detected.")
        sys.exit(1)

    if len(faces) == 1:
        selected_face = faces[0]
        step_done(f"Faces detected: 1, Confidence: {selected_face['confidence']:.1%}")
    else:
        step_done(f"Faces detected: {len(faces)}")
        console.print()
        console.print(f"[bold]{len(faces)} faces detected.[/bold]")
        console.print()
        for i, f in enumerate(faces, 1):
            x1, y1, x2, y2 = f["bbox"]
            console.print(f"  [{i}] Face at ({x1},{y1})-({x2},{y2}) confidence={f['confidence']:.1%}")
        console.print()
        choice = IntPrompt.ask("Select face number", default=1)
        if choice < 1 or choice > len(faces):
            error("Invalid selection.")
            sys.exit(1)
        selected_face = faces[choice - 1]
        console.print(f"  Selected face #{choice}")
    console.print()

    # Step 3: Face embedding
    step_header(3, TOTAL_STEPS, "Generating face embedding")
    encoder = FaceEncoder()
    try:
        embedding, enc_info = encoder.encode_from_detection(image, selected_face["bbox"])
    except Exception as e:
        step_fail("Generating face embedding", str(e))
        sys.exit(1)
    step_done("Model: ArcFace")
    console.print()

    # Step 4: Reverse image search
    step_header(4, TOTAL_STEPS, "Reverse image search")
    search_result = search_image(image_path, max_results=max_results)
    raw_results = search_result["results"]
    step_done(f"Results discovered: {len(raw_results)}")
    info(f"Provider: {search_result['provider']}")
    console.print()

    if not raw_results:
        warn("No publicly indexed visual matches found.")
        _finalize_no_results(image_path)
        return

    # Step 5: Candidate extraction & image analysis
    step_header(5, TOTAL_STEPS, "Processing candidate images")
    candidates = extract_candidates(raw_results)
    processor = CandidateProcessor()
    processed = processor.process(candidates)
    images_analyzed = sum(1 for c in processed if c.get("local_path"))
    faces_found = sum(1 for c in processed if c.get("face_detected"))
    step_done(f"Images analyzed: {images_analyzed}, Faces detected: {faces_found}")
    console.print()

    # Step 6: Face comparison & ranking
    step_header(6, TOTAL_STEPS, "Face comparison")
    ranked = rank_candidates(embedding, processed)
    step_done()
    console.print()

    if ranked:
        match_table(ranked[:10])
    else:
        warn("No candidate faces could be compared.")
    console.print()

    # Step 7: Hash generation
    step_header(7, TOTAL_STEPS, "Generating verification hash")
    input_hash = compute_file_hash(image_path)
    verification = VerificationResult(input_hash, ranked)
    verification.faces_detected = len(faces)
    step_done(f"SHA-256: {verification.record_hash[:16]}...")
    console.print()

    # Step 8: Blockchain recording
    step_header(8, TOTAL_STEPS, "Recording blockchain proof")
    client = BlockchainClient()
    if client.is_ready() and ranked:
        top = ranked[0]
        candidate_hash = top.get("url", "")
        result = client.record_verification(
            verification.record_hash,
            input_hash,
            candidate_hash,
            top.get("face_similarity", 0.0),
            True,
        )
        if result["success"]:
            verification.set_blockchain("sepolia", result["transaction_hash"])
            step_done()
            blockchain_result("sepolia", result["transaction_hash"])
        else:
            step_fail("Blockchain recording", result["error"])
            warn("Verification completed. Blockchain recording failed.")
    else:
        if not client.is_ready():
            warn("Blockchain client not configured. Skipping on-chain recording.")
            info("Set PRIVATE_KEY and CONTRACT_ADDRESS in .env to enable.")
        step_done("(skipped)")
    console.print()

    # Save result
    _save_result(verification)
    completion_banner()


def _finalize_no_results(image_path: str):
    input_hash = compute_file_hash(image_path)
    verification = VerificationResult(input_hash, [])
    verification.faces_detected = 0
    _save_result(verification)
    completion_banner()


def _save_result(verification: VerificationResult):
    results_dir = RESULTS_DIR
    results_dir.mkdir(exist_ok=True)
    existing = list(results_dir.glob("result_*.json"))
    next_num = len(existing) + 1
    save_path = results_dir / f"result_{next_num:03d}.json"

    with open(save_path, "w") as f:
        json.dump(verification.to_dict(), f, indent=2)

    console.print(f"\n  [dim]Results saved to: {save_path}[/dim]\n")


def run_verify(record_path: str):
    with open(record_path) as f:
        data = json.load(f)

    console.print("[bold]Verification Record:[/bold]")
    console.print(json.dumps(data, indent=2))
    console.print()

    client = BlockchainClient()
    if not client.is_ready():
        warn("Blockchain client not configured. Cannot verify on-chain.")
        return

    record_hash = data.get("verification_hash", "")
    result = client.get_verification(record_hash)
    if result:
        console.print("[bold green]On-chain record found:[/bold green]")
        console.print(json.dumps(result, indent=2))
    else:
        warn("No on-chain record found for this hash.")


def run_blockchain_lookup(record_hash: str):
    client = BlockchainClient()
    if not client.is_ready():
        warn("Blockchain client not configured.")
        return

    result = client.get_verification(record_hash)
    if result:
        console.print("[bold green]Verification record:[/bold green]")
        console.print(json.dumps(result, indent=2))
    else:
        warn("No record found for this hash.")


def main():
    parser = argparse.ArgumentParser(
        prog="facelens",
        description="FaceLens CLI — AI Face Search & Verification System",
    )
    subparsers = parser.add_subparsers(dest="command")

    search_parser = subparsers.add_parser("search", help="Search for a face in public web content")
    search_parser.add_argument("--image", required=True, help="Path to input image")
    search_parser.add_argument("--limit", type=int, default=20, help="Maximum results to process")

    verify_parser = subparsers.add_parser("verify", help="Verify a saved result on blockchain")
    verify_parser.add_argument("--record", required=True, help="Path to result JSON file")

    blockchain_parser = subparsers.add_parser("blockchain", help="Look up a blockchain record")
    blockchain_parser.add_argument("--hash", required=True, help="Record hash to look up")

    args = parser.parse_args()

    if args.command == "search":
        run_search(args.image, args.limit)
    elif args.command == "verify":
        run_verify(args.record)
    elif args.command == "blockchain":
        run_blockchain_lookup(args.hash)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
