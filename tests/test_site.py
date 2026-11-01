"""Build the site once and check what a visitor (or a crawler) would get.

Run: python -m pytest -q
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

import build

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    """Collects the tags and text the tests need."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.srcs: list[str] = []
        self.imgs: list[dict] = []
        self.meta: dict[str, str] = {}
        self.links: list[dict] = []
        self.h1 = 0
        self.text: list[str] = []
        self.external_blank: list[dict] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
            if a.get("target") == "_blank":
                self.external_blank.append(a)
        if tag in ("img", "script", "source") and ("src" in a or "srcset" in a):
            self.srcs.append(a.get("src") or a.get("srcset"))
        if tag == "img":
            self.imgs.append(a)
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key:
                self.meta[key] = a.get("content", "")
        if tag == "link":
            self.links.append(a)
        if tag == "h1":
            self.h1 += 1

    def handle_data(self, data):
        self.text.append(data)


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("site")
    build.render(out)
    return out


@pytest.fixture(scope="module")
def html(site) -> str:
    return (site / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def page(html) -> Page:
    p = Page()
    p.feed(html)
    return p


def test_build_writes_every_file_pages_needs(site):
    for name in ["index.html", "404.html", "robots.txt", "sitemap.xml", ".nojekyll"]:
        assert (site / name).exists(), name


def test_one_h1_and_unique_ids(page):
    assert page.h1 == 1
    dupes = {i for i in page.ids if page.ids.count(i) > 1}
    assert not dupes, f"duplicate ids: {dupes}"


def test_every_in_page_link_has_a_target(page):
    missing = [h for h in page.hrefs if h.startswith("#") and h[1:] not in page.ids]
    assert not missing, missing


def test_every_local_asset_exists(site, page):
    local = [s.split("?")[0] for s in page.srcs if not s.startswith(("http:", "https:", "data:"))]
    local += [
        link["href"].split("?")[0]
        for link in page.links
        if link.get("rel") in ("stylesheet", "icon", "apple-touch-icon")
        and not link["href"].startswith("http")
    ]
    assert local
    missing = [s for s in local if not (site / s).exists()]
    assert not missing, missing


def test_images_have_alt_text_and_size(page):
    for img in page.imgs:
        assert "alt" in img, img
        assert img.get("width") and img.get("height"), img  # avoids layout shift


def test_link_preview_and_seo_tags(site, page):
    for key in ["description", "og:title", "og:description", "og:image", "og:url", "twitter:card"]:
        assert page.meta.get(key), key
    og_image = page.meta["og:image"].split("/static/", 1)[1]
    assert (site / "static" / og_image).exists()
    assert any(link.get("rel") == "canonical" for link in page.links)


def test_new_tab_links_are_noopener(page):
    assert page.external_blank
    for a in page.external_blank:
        assert "noopener" in a.get("rel", ""), a


def test_no_phone_number_is_published(site):
    """The resume has a phone number; the public site must not."""
    phone = re.compile(r"(?:\+?91[\s-]?)?(?<!\d)[6-9]\d{4}[\s-]?\d{5}(?!\d)")
    for f in site.rglob("*"):
        if f.suffix in {".html", ".txt", ".xml", ".js", ".css", ".json"}:
            assert not phone.search(f.read_text(encoding="utf-8")), f


@pytest.mark.parametrize("name", ["anubhav-portrait.jpg", "anubhav-portrait.webp", "anubhav-avatar.jpg"])
def test_photos_carry_no_metadata(name):
    """No EXIF (camera, date, GPS) or XMP blocks in the published photos."""
    data = (ROOT / "static" / "img" / name).read_bytes()
    assert b"Exif\x00\x00" not in data
    assert b"EXIF" not in data[:4096]
    assert b"http://ns.adobe.com/xap" not in data
    assert b"Photoshop" not in data


def test_page_mentions_the_essentials(page):
    text = " ".join(page.text)
    for needle in ["Anubhav Arora", "CRIS", "BITS Pilani", "RailBook", "Terraform", "SAA-C03"]:
        assert needle in text, needle


def test_contact_links(page):
    assert any(h.startswith("mailto:") for h in page.hrefs)
    assert any("linkedin.com/in/" in h for h in page.hrefs)
    assert any(h.startswith("https://github.com/anubhav1941") for h in page.hrefs)
