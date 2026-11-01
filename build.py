"""Render content/profile.yaml into a static site.

    python build.py            # writes _site/
    python build.py --out DIR  # writes DIR/

The output is plain HTML, CSS, JS and images: GitHub Pages serves it as is.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content" / "profile.yaml"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"


def load_profile(path: Path = CONTENT) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def asset_version() -> str:
    """Short hash of the CSS and JS, appended as ?v= so browsers drop stale copies after a deploy."""
    h = hashlib.sha256()
    for f in sorted((STATIC / "css").glob("*.css")) + sorted((STATIC / "js").glob("*.js")):
        h.update(f.read_bytes())
    return h.hexdigest()[:10]


def commit_sha() -> str:
    if sha := os.environ.get("GITHUB_SHA"):
        return sha
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def json_ld(data: dict) -> dict:
    """schema.org Person, so search engines can tie the site to the LinkedIn and GitHub profiles."""
    p = data["person"]
    return {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": p["name"],
        "jobTitle": p["role"],
        "url": data["site"]["url"],
        "image": f"{data['site']['url']}/static/img/anubhav-avatar.jpg",
        "email": f"mailto:{p['email']}",
        "address": {"@type": "PostalAddress", "addressRegion": "Delhi NCR", "addressCountry": "IN"},
        "sameAs": [p["linkedin"], p["github"]],
        "alumniOf": [
            {"@type": "CollegeOrUniversity", "name": e["school"]} for e in data["education"]
        ],
        "knowsAbout": [item for g in data["skills"] for item in g["items"]][:20],
    }


def render(out: Path) -> Path:
    data = load_profile()
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "j2"]),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    build = {
        "version": asset_version(),
        "commit": commit_sha(),
        "year": datetime.now(UTC).year,
    }

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(STATIC, out / "static")

    ctx = {**data, "build": build, "jsonld": json_ld(data)}
    (out / "index.html").write_text(env.get_template("index.html.j2").render(ctx), encoding="utf-8")
    (out / "404.html").write_text(env.get_template("404.html.j2").render(ctx), encoding="utf-8")

    url = data["site"]["url"]
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}/sitemap.xml\n")
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{url}/</loc></url>\n"
        "</urlset>\n"
    )
    (out / ".nojekyll").write_text("")  # serve files as they are; no Jekyll processing
    return out / "index.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "_site", help="output directory")
    args = parser.parse_args()
    index = render(args.out)
    print(f"built {index}")


if __name__ == "__main__":
    main()
