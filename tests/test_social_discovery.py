import search.social_discovery as sd


def test_handle_variants_flat():
    variants = sd._handle_variants("Bill Gates")
    assert "billgates" in variants
    assert "bill_gates" in variants
    assert "bill-gates" in variants


def test_handle_variants_exact_case_underscore():
    variants = sd._handle_variants("Tushar Pamnani")
    assert "Tushar_Pamnani" in variants
    assert "Tushar_Pamnani_" in variants
    assert "tushar_pamnani" in variants


def test_handle_variants_single_word():
    assert sd._handle_variants("Beyonce") == ["beyonce"]


def test_discover_requires_key(monkeypatch):
    monkeypatch.setattr(sd, "REVERSE_SEARCH_API_KEY", "")
    monkeypatch.setattr(sd, "GOOGLE_CSE_KEY", "")
    monkeypatch.setattr(sd, "GOOGLE_CSE_ID", "")
    assert sd.discover_profiles_by_name("Bill Gates", set()) == {}


def test_profile_url_matches_x_com():
    assert sd._profile_url_matches("https://x.com/Tushar_Pamnani_", "twitter.com") == "Tushar_Pamnani_"
    assert sd._profile_url_matches("https://x.com/i/flow/login", "twitter.com") is None


def test_junk_handle_filtered():
    assert sd._profile_url_matches("https://www.instagram.com/tags/", "instagram.com") is None