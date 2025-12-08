# Installation and Setup

This guide covers the backend developer setup, required libraries (including WeasyPrint/GTK), and a quick Git workflow.

## System Requirements (WeasyPrint)
- **Windows developers:** Install the GTK3 runtime (e.g., `gtk3-runtime-3.24.31-2022-01-04-ts-win64`) **before** running WeasyPrint; it ships the Cairo/Pango/GDK stack WeasyPrint needs to render PDFs.
- **Linux servers/WSL:** Install the Cairo/Pango/GDK stack via your package manager, e.g. `sudo apt-get install libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info`. On container images, add these packages in the image build.
- **Mac:** Install WeasyPrint prerequisites with Homebrew (`brew install pango cairo gdk-pixbuf libffi`).
- **End users (police):** No runtime install needed; PDF generation runs on the server only.

## Python Libraries
Install these into a virtual environment:
- `Django==5.2.8`
- `djangorestframework`
- `django-storages` (cloud file handling)
- `supabase` (Supabase client)
- `python-dotenv` (load `.env`)
- `requests` (HTTP calls)
- `qrcode[pil]` (QR generation; pulls in Pillow)
- `weasyprint` (HTML → PDF)
- `psycopg2-binary` (PostgreSQL driver)
- Optional helpers depending on deployment: `gunicorn` (WSGI server), `boto3` if you swap storage backends.

## Setup Steps
1. **Clone the repo** (first time): `git clone <repo-url>`
2. **Create & activate venv** (PowerShell): `python -m venv venv; .\venv\Scripts\activate`
3. **Install Python deps:** `pip install --upgrade pip` then `pip install Django==5.2.8 djangorestframework django-storages supabase python-dotenv requests qrcode[pil] weasyprint psycopg2-binary`
4. **Install GTK (Windows only for WeasyPrint):** Run the GTK3 runtime installer noted above; restart shell afterward.
5. **Configure environment:** Create `.env` with values for `SECRET_KEY`, `GOOGLE_MAPS_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and your Postgres credentials if you override the defaults. Keep secrets out of Git.
6. **Apply migrations:** `python manage.py migrate`
7. **Run dev server:** `python manage.py runserver`
8. **Verify PDF export:** Hit a PDF endpoint (e.g., resolved cases export) to confirm WeasyPrint renders without errors.

## Git Commands We Use
- `git status` — check working tree
- `git checkout -b <branch>` — create/checkout feature branch
- `git add <path>` — stage changes
- `git commit -m "<msg>"` — commit
- `git pull` — sync with origin
- `git push -u origin <branch>` — push branch

## Deployment Notes
- Backend servers need the WeasyPrint native stack (GTK/Cairo/Pango). Add the system packages to your server image/VM. No install is needed on the users' (police) computers because PDFs are generated server-side.
- Ensure the server has access to the configured Postgres instance, Supabase keys, and Google Maps API key via environment variables.

## Deploying on a student budget (GTK included)
- **Cheapest options:**
	- Railway (free starter hours) with a Dockerfile.
	- Fly.io small VM (can fit the stack, also Dockerfile-based).
	- Render has a free tier but may sleep; still works with a Dockerfile.
- **Include GTK/Cairo/Pango in the image:** add native packages during the image build.
- **Use environment variables** for secrets (`SECRET_KEY`, `SUPABASE_*`, `GOOGLE_MAPS_API_KEY`, `DATABASE_*`).

### Minimal Dockerfile example (works on Railway/Fly/Render)
```Dockerfile
FROM python:3.11-slim

# System deps for WeasyPrint (GTK/Cairo/Pango stack)
RUN apt-get update && apt-get install -y --no-install-recommends \
		libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
		&& rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install Python deps
RUN pip install --no-cache-dir --upgrade pip \
		&& pip install --no-cache-dir Django==5.2.8 djangorestframework django-storages supabase python-dotenv requests qrcode[pil] weasyprint psycopg2-binary gunicorn

# Run migrations at startup (optional) and start gunicorn
CMD ["/bin/sh", "-c", "python manage.py migrate && gunicorn crash_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
```

### Deploy steps (Docker-based, e.g., Railway/Fly/Render)
1. Commit code and ensure `docs/Installation_and_Setup.md` and `Dockerfile` are in repo.
2. Add env vars in the platform dashboard (`SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GOOGLE_MAPS_API_KEY`, Postgres creds). Use the platform’s managed Postgres if available.
3. Point the platform to the repo; it builds the Dockerfile, which installs GTK deps and Python libs.
4. After deploy, hit a PDF endpoint to confirm WeasyPrint works (no missing `cairo/pango` errors).
5. Keep secrets out of Git; rotate keys if they were ever committed.
