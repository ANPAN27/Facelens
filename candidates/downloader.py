import requests
from pathlib import Path

from config import DOWNLOAD_TIMEOUT, MAX_CANDIDATE_IMAGES


def download_image(url: str, save_dir: str, index: int) -> str | None:
    try:
        resp = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type and not url.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return None

        ext = ".jpg"
        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"

        save_path = Path(save_dir) / f"candidate_{index:03d}{ext}"
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        if save_path.stat().st_size < 100:
            save_path.unlink()
            return None

        return str(save_path)
    except Exception:
        return None
