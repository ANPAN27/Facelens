import hashlib
import base64
import json
from pathlib import Path

import requests

from config import REVERSE_SEARCH_API_KEY, REVERSE_SEARCH_PROVIDER, GOOGLE_LENS
from search.base import ReverseSearchProvider
from search.providers.provider import SerpApiProvider, ScraperProvider, GoogleLensProvider


def get_provider(name: str | None = None) -> ReverseSearchProvider:
    provider = name or REVERSE_SEARCH_PROVIDER
    if provider == "serpapi" and REVERSE_SEARCH_API_KEY:
        return SerpApiProvider(api_key=REVERSE_SEARCH_API_KEY)
    return ScraperProvider()


def _has_errors(results: list[dict]) -> bool:
    return any(r.get("error") for r in results)


def _search_target(provider: ReverseSearchProvider, target: str, face_match: bool) -> tuple[list[dict], bool, str]:
    results = provider.search(target)
    had_errors = _has_errors(results)
    errors = [r.get("error") for r in results if r.get("error")]
    clean = [dict(r, face_match=face_match) for r in results if not r.get("error")]
    return clean, had_errors, errors[0] if errors else ""


def _lens_results(fallback_targets: list[tuple[str, bool]]) -> tuple[list[dict], str]:
    if not GOOGLE_LENS or not REVERSE_SEARCH_API_KEY:
        return [], ""
    lens = GoogleLensProvider(api_key=REVERSE_SEARCH_API_KEY)
    results: list[dict] = []
    error = ""
    for target, is_crop in fallback_targets:
        if results:
            break
        try:
            found = lens.search(target)
        except Exception as e:
            error = str(e)
            found = []
        errs = [r.get("error") for r in found if r.get("error")]
        if errs:
            error = errs[0]
        results = [dict(r, face_match=True) for r in found if not r.get("error")]
    return results, error


def search_image(
    image_path: str,
    provider_name: str | None = None,
    max_results: int = 20,
    face_crop_path: str | None = None,
) -> dict:
    primary = get_provider(provider_name)
    combined: list[dict] = []
    chosen_label = "none"
    warning = ""

    targets: list[tuple[str, str, bool]] = []
    if face_crop_path:
        targets.append(("face-crop", face_crop_path, True))
    targets.append(("full-image", image_path, False))

    for label, target, is_crop in targets:
        if combined:
            break
        target_results, had_errors, target_error = _search_target(primary, target, is_crop)
        if had_errors and not warning:
            warning = target_error or "search provider returned an error"
        if target_results:
            combined = target_results
            chosen_label = label

    engine_counts = {"serpapi_reverse": len(combined), "google_lens": 0}

    # Google Lens (identity/feature matching) on face crop first, then full image.
    lens_targets: list[tuple[str, bool]] = []
    if face_crop_path:
        lens_targets.append((face_crop_path, True))
    lens_targets.append((image_path, False))
    lens_extra, lens_error = _lens_results(lens_targets)
    if lens_error and not warning:
        warning = lens_error
    for r in lens_extra:
        if r not in combined:
            combined.append(r)

    if not combined and not lens_extra:
        fallback_results, _, fallback_error = _search_target(ScraperProvider(), image_path, False)
        if fallback_error and not warning:
            warning = fallback_error
        if fallback_results:
            combined = fallback_results
            chosen_label = "full-image"

    seen_urls = set()
    unique = []
    for r in combined:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)

    unique.sort(key=lambda r: 0 if r.get("face_match") else 1)

    lens_count = len([r for r in combined if r.get("source") == "google-lens"])
    provider_label = primary.name()
    if lens_count:
        provider_label = f"{provider_label}+google-lens"

    return {
        "provider": provider_label,
        "total_results": len(unique),
        "results": unique[:max_results],
        "searched_image": chosen_label,
        "warning": warning,
    }