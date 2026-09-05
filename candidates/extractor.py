from urllib.parse import urlparse


def extract_candidates(search_results: list[dict]) -> list[dict]:
    candidates = []
    for r in search_results:
        if r.get("error"):
            continue

        url = r.get("url", "")
        if not url:
            continue

        domain = r.get("domain") or urlparse(url).netloc
        image_url = r.get("image_url", "")

        candidates.append({
            "title": r.get("title", ""),
            "url": url,
            "domain": domain,
            "image_url": image_url,
            "platform": r.get("platform", "Unknown"),
            "source": r.get("source", ""),
        })

    return candidates
