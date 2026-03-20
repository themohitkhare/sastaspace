# tests/test_deployer.py
import json

from sastaspace.deployer import (
    deploy,
    derive_subdomain,
    load_registry,
)

SAMPLE_HTML = "<!DOCTYPE html><html><body>hi</body></html>"


# --- derive_subdomain tests ---


def test_derive_subdomain_simple():
    assert derive_subdomain("https://acme.com") == "acme-com"


def test_derive_subdomain_strips_www():
    assert derive_subdomain("https://www.acme.com") == "acme-com"


def test_derive_subdomain_complex():
    result = derive_subdomain("https://www.acme-corp.co.uk/shop")
    assert result == "acme-corp-co-uk"


def test_derive_subdomain_lowercase():
    assert derive_subdomain("https://MYSITE.COM") == "mysite-com"


def test_derive_subdomain_truncates_long():
    long_url = "https://this-is-a-very-long-domain-name-that-exceeds-fifty-characters.com"
    result = derive_subdomain(long_url)
    assert len(result) <= 50


def test_derive_subdomain_no_trailing_hyphens():
    result = derive_subdomain("https://acme.com/")
    assert not result.endswith("-")
    assert not result.startswith("-")


# --- deploy() tests ---


def test_deploy_creates_index_html(tmp_path):
    result = deploy(
        url="https://acme.com",
        html=SAMPLE_HTML,
        sites_dir=tmp_path,
    )
    index = tmp_path / result.subdomain / "index.html"
    assert index.exists()
    assert index.read_text() == SAMPLE_HTML


def test_deploy_creates_metadata_json(tmp_path):
    result = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    meta_path = tmp_path / result.subdomain / "metadata.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["original_url"] == "https://acme.com"
    assert meta["subdomain"] == result.subdomain
    assert "timestamp" in meta


def test_deploy_updates_registry(tmp_path):
    deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    deploy(url="https://beta.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    registry = load_registry(tmp_path)
    subdomains = [e["subdomain"] for e in registry]
    assert "acme-com" in subdomains
    assert "beta-com" in subdomains


def test_deploy_collision_appends_suffix(tmp_path):
    r1 = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    r2 = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    assert r1.subdomain != r2.subdomain
    assert r2.subdomain.startswith("acme-com")


def test_deploy_returns_deploy_result(tmp_path):
    result = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    assert hasattr(result, "subdomain")
    assert hasattr(result, "index_path")
    assert result.index_path.exists()


def test_deploy_atomic_registry_no_tmp_leftover(tmp_path):
    deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    tmp_registry = tmp_path / "_registry.json.tmp"
    assert not tmp_registry.exists()


# --- load_registry tests ---


def test_load_registry_returns_empty_list_when_missing(tmp_path):
    registry = load_registry(tmp_path)
    assert registry == []


def test_load_registry_returns_list(tmp_path):
    deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    registry = load_registry(tmp_path)
    assert isinstance(registry, list)
    assert len(registry) == 1
