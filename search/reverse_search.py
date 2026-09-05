import hashlib
import base64
import json
from pathlib import Path

import requests

from config import REVERSE_SEARCH_API_KEY, REVERSE_SEARCH_PROVIDER
from search.base import ReverseSearchProvider
from search.providers.provider import SerpApiProvider, ScraperProvider


def get_provider(name: str | None = None) -> ReverseSearchProvider:
    provider = name or REVERSE_SEARCH_PROVIDER
    if provider == "serpapi" and REVERSE_SEARCH_API_KEY:
        return SerpApiProvider(api_key=REVERSE_SEARCH_API_KEY)
    return ScraperProvider()


def _has_errors(results: list[dict]) -> bool:
    return any(r.get("error") for r in results)


def search_image(image_path: str, provider_name: str | None = None, max_results: int = 20) -> dict:
    primary = get_provider(provider_name)
    primary_results = primary.search(image_path)

    if _has_errors(primary_results) or not primary_results:
        fallback = ScraperProvider()
        fallback_results = fallback.search(image_path)
    else:
        fallback_results = []

    combined = [r for r in primary_results if not r.get("error")]
    for r in fallback_results:
        if r not in combined:
            combined.append(r)

    seen_urls = set()
    unique = []
    for r in combined:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)

    summary_source = primary.name()
    if _has_errors(primary_results) and fallback_results:
        summary_source = f"{primary.name()}+bing-fallback"

    return {
        "provider": summary_source,
        "total_results": len(unique),
        "results": unique[:max_results],
    }