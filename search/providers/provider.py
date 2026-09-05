import base64
import json
import re
from pathlib import Path
from urllib.parse import urlparse, quote_plus
from html import unescape

import requests

from search.base import ReverseSearchProvider
from config import DOWNLOAD_TIMEOUT


def upload_to_host(image_path: str) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    size_error = None if img_bytes else "empty file"

    try:
        files = {"fileToUpload": ("image.jpg", img_bytes, "image/jpeg")}
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files=files,
            timeout=45,
            headers=headers,
        )
        url = resp.text.strip()
        if resp.status_code == 200 and url.startswith("http") and "error" not in url.lower():
            return url
    except Exception as e:
        size_error = str(e)

    try:
        files = {"file": ("image.jpg", img_bytes, "image/jpeg")}
        resp = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files=files,
            timeout=45,
            headers=headers,
        )
        data = resp.json()
        url = data.get("data", {}).get("url", "")
        if url:
            m = re.search(r"tmpfiles\.org/([^/]+/[^/]+)", url)
            if m:
                return f"https://tmpfiles.org/dl/{m.group(1)}"
    except Exception:
        pass

    return None


class SerpApiProvider(ReverseSearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search.json"

    def name(self) -> str:
        return "serpapi"

    def search(self, image_path: str) -> list[dict]:
        hosted = upload_to_host(image_path)
        if not hosted:
            return [{"error": "Could not host image for search"}]

        try:
            resp = requests.get(
                self.base_url,
                params={"engine": "google_reverse_image", "api_key": self.api_key, "image_url": hosted},
                timeout=45,
            )
            data = resp.json()
        except Exception as e:
            return [{"error": str(e)}]

        if "error" in data:
            return [{"error": data["error"]}]

        results = []
        for item in data.get("image_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "domain": urlparse(item.get("link", "")).netloc,
                "image_url": item.get("original") or item.get("thumbnail", ""),
                "platform": self._detect_platform(item.get("link", "")),
                "source": "serpapi",
            })

        for item in data.get("inline_images", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("source", ""),
                "domain": urlparse(item.get("source", "")).netloc,
                "image_url": item.get("original", ""),
                "platform": "Image",
                "source": "serpapi",
            })

        return results

    def _detect_platform(self, url: str) -> str:
        return detect_platform(url)


class ScraperProvider(ReverseSearchProvider):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def name(self) -> str:
        return "bing"

    def search(self, image_path: str) -> list[dict]:
        hosted = upload_to_host(image_path)
        if not hosted:
            return []

        results = self._search_bing(hosted)
        if not results:
            results = self._search_yandex(image_path)

        return results

    def _search_bing(self, image_url: str) -> list[dict]:
        results = []
        try:
            self.session.get("https://www.bing.com/", timeout=DOWNLOAD_TIMEOUT)
            query = f"imgurl:{image_url}"
            search_url = (
                f"https://www.bing.com/images/search?q={quote_plus(query)}"
                f"&view=detailv2&iss=sbi&form=SBIHMP&sbifs=0"
            )

            resp = self.session.get(search_url, timeout=30, allow_redirects=True)
            if resp.status_code != 200:
                return []

            html = resp.text

            seen = set()
            for m in re.finditer(r'm="(.*?)"', html):
                raw = unescape(m.group(1))
                try:
                    obj = json.loads(raw)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue

                media_url = (obj.get("murl") or "").strip()
                page_url = (obj.get("purl") or "").strip()
                if not media_url or not page_url:
                    continue
                if page_url in seen:
                    continue
                seen.add(page_url)

                results.append({
                    "title": (obj.get("title") or "").strip(),
                    "url": page_url,
                    "domain": urlparse(page_url).netloc,
                    "image_url": media_url,
                    "platform": detect_platform(page_url),
                    "source": "bing",
                })
                if len(results) >= 20:
                    break
        except Exception:
            pass
        return results

    def _search_yandex(self, image_path: str) -> list[dict]:
        results = []
        try:
            with open(image_path, "rb") as f:
                resp = self.session.post(
                    "https://yandex.com/images/search?rpt=imageview&format=json",
                    files={"upfile": ("image.jpg", f, "image/jpeg")},
                    timeout=DOWNLOAD_TIMEOUT,
                )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    items = data.get("cbir-page", {}).get("items", [])
                    for item in items:
                        url = item.get("link", "") or item.get("url", "")
                        if url:
                            results.append({
                                "title": item.get("title", ""),
                                "url": url,
                                "domain": urlparse(url).netloc,
                                "image_url": item.get("media", "") or item.get("thumbnail", ""),
                                "platform": detect_platform(url),
                                "source": "yandex",
                            })
                except Exception:
                    pass
        except Exception:
            pass
        return results


def safe_json_str(raw: str) -> str:
    if not raw or raw in ('""', "null"):
        return ""
    try:
        return unescape(json.loads(raw))
    except Exception:
        return raw.strip('"').replace('\\"', '"')


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    platforms = {
        "instagram.com": "Instagram",
        "facebook.com": "Facebook",
        "x.com": "X/Twitter",
        "twitter.com": "X/Twitter",
        "linkedin.com": "LinkedIn",
        "reddit.com": "Reddit",
        "tiktok.com": "TikTok",
        "pinterest.com": "Pinterest",
        "youtube.com": "YouTube",
        "flickr.com": "Flickr",
        "tumblr.com": "Tumblr",
    }
    for key, name in platforms.items():
        if key in domain:
            return name
    return "Website"