from profiles.extractor import (
    extract_profiles_from_text,
    extract_social_profiles,
    _url_profile_handles,
)


def test_url_profile_handles_instagram():
    found = list(_url_profile_handles("https://www.instagram.com/elonmusk/"))
    assert found and found[0] == ("Instagram", "elonmusk")


def test_instagram_post_not_handled_as_profile():
    assert list(_url_profile_handles("https://www.instagram.com/p/CxYz123/")) == []


def test_twitter_status_not_a_profile():
    assert list(_url_profile_handles("https://twitter.com/elonmusk/status/12345")) == [("X/Twitter", "elonmusk")]


def test_tiktok_handle():
    found = list(_url_profile_handles("https://www.tiktok.com/@mrbeast"))
    assert found and found[0] == ("TikTok", "mrbeast")


def test_youtube_channel():
    found = list(_url_profile_handles("https://www.youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA"))
    assert found and found[0] == ("YouTube", "UCX6OQ3DkcsbYNE6H8uQQuVA")


def test_linkedin_person():
    found = list(_url_profile_handles("https://www.linkedin.com/in/john-doe-123/"))
    assert found and found[0][0] == "LinkedIn"


def test_tumblr_subdomain():
    found = list(_url_profile_handles("https://exampleblog.tumblr.com/"))
    assert found and found[0] == ("Tumblr", "exampleblog")


def test_reserved_paths_skipped():
    assert list(_url_profile_handles("https://twitter.com/hashtag/elon")) == []
    assert list(_url_profile_handles("https://www.youtube.com/watch?v=abc123")) == []


def test_extract_from_text_multiple():
    html = """
    <a href="https://www.instagram.com/natgeo">IG</a>
    <a href="https://twitter.com/NatGeo">tweet</a>
    <a href="https://open.spotify.com/user/x">not handled</a>
    """
    found = set(extract_profiles_from_text(html))
    assert ("Instagram", "natgeo") in found
    assert ("X/Twitter", "NatGeo") in found


def test_extract_profiles_from_results_links_only():
    results = [
        {"url": "https://www.instagram.com/janedoe/", "domain": "instagram.com"},
        {"url": "https://www.linkedin.com/in/jane-doe", "domain": "linkedin.com"},
        {"url": "https://someblog.example/post/123", "domain": "someblog.example"},
    ]
    profiles = extract_social_profiles(results, max_pages=0)
    assert "Instagram" in profiles
    assert "LinkedIn" in profiles
    assert "https://instagram.com/janedoe" in profiles["Instagram"]
    assert "https://linkedin.com/in/jane-doe" in profiles["LinkedIn"]