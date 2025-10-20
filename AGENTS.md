## Overview

This repository fetches data from the Yahoo Fantasy Sports API and renders static HTML pages with Jinja2. The main entrypoint is `src/fetch_and_build.py`, which pulls league data using the credentials in `dev.env` and writes the generated site to `site/`.

## Environment

- Requires Python 3.12 (see `venv/` and `requirements.txt`).
- Copy or edit `dev.env` with Yahoo app credentials. The build script automatically loads this file.
- Never commit real credentials. Use placeholder values if you need to share the file.

### Initial setup

```bash
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Working Locally

1. Activate the virtualenv: `. venv/bin/activate`
2. Export the environment variables for the session (optional if `dev.env` already has working values):
   ```bash
   set -a
   source dev.env
   set +a
   ```
3. Run `python src/fetch_and_build.py`. Successful runs print `✅ Build complete.` and refresh the static files in `site/`.
4. Open `site/index.html` in a browser to review the rendered results.

## Testing and Validation

- There is no automated test suite yet. Use manual validation:
  - Inspect the console output for HTTP or template errors.
  - Sanity‑check the JSON snapshots in `data/` if something looks off.
  - Review updated pages in the `site/` directory.
- When changing templates, re-run the build script to make sure Jinja renders cleanly.

## Deployment Notes

- The generated site is static. Deploy the `site/` directory to any static host (GitHub Pages, Netlify, etc.).
- Update `site/sitemap.txt` values to match your hosting URL before publishing.

## Troubleshooting

- `KeyError` for an environment variable → ensure `dev.env` exists and contains the needed keys or that the variables are exported in the shell.
- Yahoo API 401/403 errors → refresh the `YAHOO_REFRESH_TOKEN` or confirm the app has access to the league.
- Template syntax errors usually show up during build; fix the offending file in `src/templates/` and rebuild.
