# anubhav1941.github.io

Personal site of **Anubhav Arora**, Cloud, DevOps & Platform Engineer. Live at <https://anubhav1941.github.io>.

A single static page rendered from one YAML file. No framework and no client-side build: plain HTML, CSS and a few lines of JavaScript, so it loads fast and works without JavaScript.

## How it works

```
content/profile.yaml ──▶ build.py (Jinja2) ──▶ _site/ ──▶ GitHub Pages
                              ▲
templates/*.j2 ───────────────┘   static/ (CSS, JS, images) copied as is
```

Every push to `main` runs [`.github/workflows/pages.yml`](.github/workflows/pages.yml): install, `pytest`, build, deploy. Pull requests run the tests and the build without deploying.

## Edit the content

Change `content/profile.yaml` (experience, projects, skills, certifications) and push. Diagrams are inline SVG in `templates/diagrams.html.j2` and follow the light/dark theme.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # builds the site and checks it
python build.py              # writes _site/
python -m http.server -d _site 8000
```

## What the tests check

- Every in-page link has a target, ids are unique, there is one `<h1>`.
- Every referenced CSS, JS and image file exists; images have alt text and dimensions.
- Link-preview (Open Graph) and SEO tags are present, and the preview image exists.
- New-tab links use `rel="noopener"`.
- **Privacy:** no phone number anywhere in the output, and the photos carry no EXIF, XMP or Photoshop metadata.

## Link-preview image

`static/img/og.png` is a screenshot of `tools/og.html` at 1200×630. Open that file in a browser at that size and capture it to regenerate.

## One-time setup

Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**.
