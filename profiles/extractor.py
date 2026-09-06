import re
from urllib.parse import urlparse

import requests

from config import SOCIAL_PAGE_TIMEOUT, MAX_PROFILE_PAGES
from search.providers.provider import detect_platform


def _canon(platform, handle):
    builders = {
        "Instagram": lambda h: f"https://instagram.com/{h}",
        "Threads": lambda h: f"https://threads.net/@{h}",
        "Facebook": lambda h: f"https://facebook.com/{h}",
        "X/Twitter": lambda h: f"https://x.com/{h}",
        "TikTok": lambda h: f"https://tiktok.com/@{h}",
        "LinkedIn": lambda h: f"https://linkedin.com/in/{h}",
        "YouTube": lambda h: f"https://youtube.com/@{h}" if not h.startswith("UC") else f"https://youtube.com/channel/{h}",
        "Pinterest": lambda h: f"https://pinterest.com/{h}",
        "Reddit": lambda h: f"https://reddit.com/user/{h}",
        "Telegram": lambda h: f"https://t.me/{h}",
        "Snapchat": lambda h: f"https://snapchat.com/add/{h}",
        "GitHub": lambda h: f"https://github.com/{h}",
        "Twitch": lambda h: f"https://twitch.tv/{h}",
        "SoundCloud": lambda h: f"https://soundcloud.com/{h}",
        "Medium": lambda h: f"https://medium.com/@{h}",
        "Flickr": lambda h: f"https://flickr.com/photos/{h}",
        "DeviantArt": lambda h: f"https://deviantart.com/{h}",
        "OnlyFans": lambda h: f"https://onlyfans.com/{h}",
    }
    return builders.get(platform, lambda h: f"https://{h}")(handle)


# platform -> (regex, reserved). Handles greedily consume non-delimiter chars,
# so `/ ? # " ' < > & ;` naturally terminate the profile handle.
_PATTERNS = [
    (
        "Instagram",
        re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9_.]{1,30})", re.I),
        {"p", "reel", "tv", "stories", "explore", "about", "accounts", "settings", "login", "signup",
         "discover", "people", "developers", "legal", "privacy", "help", "notifications", "activity", "0"},
    ),
    (
        "Threads",
        re.compile(r"(?:https?://)?(?:www\.)?threads\.net/(?:@)?([A-Za-z0-9_.]{1,30})", re.I),
        {"intent", "settings", "login", "signup", "search", "about", "profile"},
    ),
    (
        "Facebook",
        re.compile(r"(?:https?://)?(?:www\.)?(?:facebook\.com|fb\.com)/([A-Za-z0-9_.-]{3,50})", re.I),
        {"home", "login", "signup", "photos", "video", "videos", "groups", "events", "marketplace", "messages",
         "friends", "settings", "about", "help", "legal", "people", "photo", "watch", "shorts", "me",
         "stories", "bookmarks", "pages", "reel", "profile", "admin", "business", "fundraisers"},
    ),
    (
        "X/Twitter",
        re.compile(r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([A-Za-z0-9_]{1,15})", re.I),
        {"home", "search", "explore", "notifications", "messages", "i", "intents", "hashtag", "status",
         "shared", "account", "settings", "login", "signup", "about", "tos", "privacy", "help",
         "compose", "jot", "verified", "mentions", "lists", "who_to_follow", "search-advanced"},
    ),
    (
        "TikTok",
        re.compile(r"(?:https?://)?(?:www\.)?tiktok\.com/@([A-Za-z0-9_.-]{1,30})", re.I),
        {"fyp", "home", "login", "signup", "discover", "search", "about", "creator", "music", "tag",
         "embed", "share", "feedback", "trending", "explore"},
    ),
    (
        "LinkedIn",
        re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company|pub)/([A-Za-z0-9_-]{1,100})", re.I),
        {"feed", "jobs", "search", "login", "signup", "profile", "groups", "events", "marketing",
         "sales", "talent", "learning", "home", "dei", "pulse", "advice", "skill"},
    ),
    (
        "YouTube",
        re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/(channel/UC[A-Za-z0-9_-]{22}|(?:@|user/)?[A-Za-z0-9_.-]{1,50})", re.I),
        {"watch", "playlist", "results", "feed", "trending", "about", "shorts", "embed", "account",
         "upload", "live", "post", "channel", "user", "playlists", "music", "gaming", "news"},
    ),
    (
        "Pinterest",
        re.compile(r"(?:https?://)?(?:www\.)?pinterest\.[a-z.]+/([A-Za-z0-9_-]{3,40})", re.I),
        {"pin", "pins", "explore", "ideas", "search", "about", "login", "signup", "settings", "news",
         "collections", "today", "home", "messages", "notifications", "topic", "boards"},
    ),
    (
        "Reddit",
        re.compile(r"(?:https?://)?(?:www\.)?reddit\.com/(?:u|user)/([A-Za-z0-9_-]{1,25})", re.I),
        {"settings", "apps", "account", "login", "submit", "top", "new", "hot", "rising", "best"},
    ),
    (
        "Telegram",
        re.compile(r"(?:https?://)?(?:www\.)?t\.me/([A-Za-z0-9_]{1,32})", re.I),
        {"joinchat", "addstickers", "share", "proxy", "en", "login", "about", "privacy", "settings", "s", "addtheme"},
    ),
    (
        "Snapchat",
        re.compile(r"(?:https?://)?(?:www\.)?snapchat\.com/add/([A-Za-z0-9_.]{1,20})", re.I),
        {"about", "login", "signup", "en-US", "lenses", "discover"},
    ),
    (
        "GitHub",
        re.compile(r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9-]{1,39})", re.I),
        {"about", "features", "login", "explore", "marketplace", "events", "settings", "topics",
         "sponsors", "logos", "collections", "trending", "search", "pricing", "signup", "contact",
         "security", "enterprise", "blog", "site", "customer-stories", "solutions"},
    ),
    (
        "Twitch",
        re.compile(r"(?:https?://)?(?:www\.)?twitch\.tv/([A-Za-z0-9_]{1,25})", re.I),
        {"about", "directory", "downloads", "jobs", "settings", "login", "signup", "search", "turbo", "partner", "subscriptions"},
    ),
    (
        "SoundCloud",
        re.compile(r"(?:https?://)?(?:www\.)?soundcloud\.com/([A-Za-z0-9_-]{1,40})", re.I),
        {"explore", "stream", "search", "upload", "signin", "settings", "you", "feed", "notifications",
         "messages", "popular", "charts", "featured", "for-artists", "pages", "download", "improve"},
    ),
    (
        "Medium",
        re.compile(r"(?:https?://)?(?:www\.)?medium\.com/@([A-Za-z0-9_.-]{1,40})", re.I),
        {"about", "signup", "login", "settings", "publish", "tag", "topic", "search", "sponsorships", "bookmark", "topics"},
    ),
    (
        "Flickr",
        re.compile(r"(?:https?://)?(?:www\.)?flickr\.com/photos/([A-Za-z0-9@_.-]{1,50})", re.I),
        {"upload", "exchange", "gallery", "explore", "search", "groups", "settings", "learn", "about", "fluidr"},
    ),
    (
        "Tumblr",
        re.compile(r"(?:https?://)?([A-Za-z0-9][A-Za-z0-9-]{1,30})\.tumblr\.com", re.I),
        {"www", "staff", "about", "docs", "privacy", "login", "signup", "explore", "tagged", "dashboard", "tools"},
    ),
    (
        "DeviantArt",
        re.compile(r"(?:https?://)?(?:www\.)?deviantart\.com/([A-Za-z0-9_-]{2,30})", re.I),
        {"about", "staff", "login", "signup", "settings", "featured", "popular", "search", "explore",
         "journal", "profile", "shop", "categories", "join-us", "status", "certified", "art", "blog", "awards", "moving"},
    ),
    (
        "OnlyFans",
        re.compile(r"(?:https?://)?(?:www\.)?onlyfans\.com/([A-Za-z0-9_.]{1,40})", re.I),
        {"about", "signup", "login", "terms", "products", "create", "search", "explore", "messages", "my", "pricing"},
    ),
]

_RESERVED = {platform_name: res for platform_name, _, res in _PATTERNS}


def _norm(platform: str, handle: str) -> str:
    if platform == "YouTube":
        handle = handle.removeprefix("channel/").removeprefix("user/").removeprefix("@")
    return handle


def _complete_url(match) -> str:
    return match.group(0)


def _url_profile_handles(url: str):
    """Yield (platform, raw_handle) candidates from a URL if it looks like a profile link."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().replace("www.", "")
    path = (parsed.path or "").lstrip("/")
    if not host or "." not in host:
        return
    for platform, rx, _ in _PATTERNS:
        m = rx.search(url)
        if m:
            h = _norm(platform, m.group(1))
            if h and h.lower() not in _RESERVED[platform]:
                yield platform, h


def extract_profiles_from_text(text: str, base_host: str = ""):
    """Extract social profile handles from arbitrary text (HTML), deduped."""
    found = set()
    for platform, rx, _ in _PATTERNS:
        for m in rx.finditer(text):
            h = _norm(platform, m.group(1))
            if h and h.lower() not in _RESERVED[platform]:
                if base_host and base_host == f"{h}.tumblr.com":
                    continue
                found.add((platform, h))
    return sorted(found, key=lambda x: (x[0], x[1].lower()))


def extract_social_profiles(results: list[dict], max_pages: int = MAX_PROFILE_PAGES) -> dict:
    """Build {platform: [profile_url,...]} from result page URLs + scanned page content."""
    profiles: dict[str, set] = {}
    page_urls = [r.get("url", "") for r in results if r.get("url")]

    for url in page_urls:
        for platform, handle in _url_profile_handles(url):
            profiles.setdefault(platform, set()).add(_canon(platform, handle))

    scanned = 0
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    for url in page_urls:
        if scanned >= max_pages:
            break
        if not url.startswith("http"):
            continue
        platform = detect_platform(url)
        if platform in {"Instagram", "X/Twitter", "TikTok", "LinkedIn", "YouTube", "Facebook", "Pinterest", "Reddit", "Tumblr", "Snapchat", "DeviantArt", "Telegram", "GitHub", "Medium"}:
            continue
        scanned += 1
        try:
            resp = session.get(url, timeout=SOCIAL_PAGE_TIMEOUT, allow_redirects=True)
            if resp.status_code != 200:
                continue
            for platform, handle in extract_profiles_from_text(resp.text, urlparse(url).netloc):
                profiles.setdefault(platform, set()).add(_canon(platform, handle))
        except Exception:
            continue

    return {p: sorted(u) for p, u in profiles.items()}