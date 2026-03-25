# tests/test_urls.py
"""Tests for URL normalization, validation, and SSRF protection."""

from sastaspace.urls import extract_domain, is_valid_url, normalize_url, url_hash

# --- normalize_url tests ---


class TestNormalizeUrl:
    def test_bare_domain(self):
        assert normalize_url("example.com") == "https://example.com"

    def test_http_to_https(self):
        assert normalize_url("http://example.com") == "https://example.com"

    def test_strips_www(self):
        assert normalize_url("www.example.com") == "https://example.com"

    def test_strips_trailing_slash(self):
        assert normalize_url("example.com/") == "https://example.com"

    def test_lowercases(self):
        assert normalize_url("Example.COM") == "https://example.com"

    def test_preserves_path(self):
        assert normalize_url("example.com/about") == "https://example.com/about"

    def test_preserves_non_standard_port(self):
        assert normalize_url("example.com:8080") == "https://example.com:8080"

    def test_strips_standard_port_443(self):
        assert normalize_url("https://example.com:443") == "https://example.com"

    def test_strips_standard_port_80(self):
        assert normalize_url("http://example.com:80") == "https://example.com"

    def test_strips_query_string(self):
        assert normalize_url("example.com?foo=bar") == "https://example.com"

    def test_strips_fragment(self):
        assert normalize_url("example.com#section") == "https://example.com"

    def test_empty_string(self):
        assert normalize_url("") == ""

    def test_whitespace(self):
        assert normalize_url("  example.com  ") == "https://example.com"


# --- url_hash tests ---


class TestUrlHash:
    def test_deterministic(self):
        assert url_hash("example.com") == url_hash("example.com")

    def test_normalizes_before_hashing(self):
        assert url_hash("http://www.example.com/") == url_hash("example.com")

    def test_different_domains_different_hash(self):
        assert url_hash("example.com") != url_hash("other.com")

    def test_returns_16_char_hex(self):
        h = url_hash("example.com")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)


# --- extract_domain tests ---


class TestExtractDomain:
    def test_simple_domain(self):
        assert extract_domain("example.com") == "example.com"

    def test_with_subdomain(self):
        assert extract_domain("blog.example.com") == "example.com"

    def test_with_path(self):
        assert extract_domain("example.com/path") == "example.com"

    def test_co_uk(self):
        assert extract_domain("blog.example.co.uk") == "example.co.uk"

    def test_with_protocol(self):
        assert extract_domain("https://example.com") == "example.com"


# --- is_valid_url SSRF protection tests ---


class TestIsValidUrl:
    def test_valid_domain(self):
        valid, result = is_valid_url("example.com")
        assert valid
        assert result == "https://example.com"

    def test_valid_with_path(self):
        valid, result = is_valid_url("example.com/about")
        assert valid

    def test_empty(self):
        valid, msg = is_valid_url("")
        assert not valid
        assert "enter a website" in msg.lower()

    def test_whitespace_only(self):
        valid, msg = is_valid_url("   ")
        assert not valid

    def test_too_long(self):
        valid, msg = is_valid_url("a" * 3000 + ".com")
        assert not valid
        assert "too long" in msg.lower()

    def test_no_tld(self):
        valid, msg = is_valid_url("notawebsite")
        assert not valid

    # --- SSRF blocks ---

    def test_blocks_localhost(self):
        valid, msg = is_valid_url("localhost")
        assert not valid
        assert "localhost" in msg.lower()

    def test_blocks_127_0_0_1(self):
        valid, msg = is_valid_url("127.0.0.1")
        assert not valid

    def test_blocks_0_0_0_0(self):
        valid, msg = is_valid_url("0.0.0.0")
        assert not valid

    def test_blocks_ipv6_loopback(self):
        valid, msg = is_valid_url("::1")
        assert not valid

    def test_blocks_private_192_168(self):
        valid, msg = is_valid_url("192.168.1.1")
        assert not valid

    def test_blocks_private_10(self):
        valid, msg = is_valid_url("10.0.0.1")
        assert not valid

    def test_blocks_private_172(self):
        valid, msg = is_valid_url("172.16.0.1")
        assert not valid

    def test_blocks_link_local(self):
        valid, msg = is_valid_url("169.254.169.254")
        assert not valid

    def test_blocks_aws_metadata(self):
        valid, msg = is_valid_url("169.254.169.254")
        assert not valid
        assert "internal" in msg.lower()

    def test_blocks_gcp_metadata(self):
        valid, msg = is_valid_url("metadata.google.internal")
        assert not valid

    def test_blocks_non_http_scheme(self):
        valid, msg = is_valid_url("ftp://example.com")
        assert not valid

    def test_blocks_javascript_scheme(self):
        valid, msg = is_valid_url("javascript:alert(1)")
        assert not valid

    def test_blocks_hex_ip(self):
        valid, msg = is_valid_url("0x7f000001")
        assert not valid

    def test_blocks_octal_ip(self):
        valid, msg = is_valid_url("0177.0.0.1")
        assert not valid
