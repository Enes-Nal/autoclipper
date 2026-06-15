# Render + Cloudflare R2 Deployment Design

**Date:** 2026-06-14
**Status:** Approved

## Overview

Deploy the Flask video editor (autoclipper) to Render's free tier, using Cloudflare R2 as persistent object storage for templates and exported videos. Everything else (downloads, uploads, temp files) remains ephemeral local disk.

## What Goes to R2

| Directory | R2? | Reason |
|---|---|---|
| `templates/` | Yes — sync on startup, write-through | Must survive restarts |
| `exports/` | Yes — upload after generation, serve presigned URL | User must download finished video |
| `downloads/` | No | Temporary working file, always re-downloadable |
| `uploads/` | No | Ephemeral; user re-uploads as needed |
| `sfx/` | No | Not fully implemented yet |
| `temp/` | No | Processing scratch space |

## Architecture

### New module: `storage.py`

Wraps all R2 interaction via `boto3` (S3-compatible API). Configured by four env vars:

- `R2_ENDPOINT_URL` — e.g. `https://<account-id>.r2.cloudflarestorage.com`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`

If any of these are absent, all `storage.py` functions are no-ops — the app works unchanged in local dev without any R2 config.

Public API:
- `sync_templates_from_r2(templates_dir)` — lists `templates/` prefix in R2, writes missing/newer files to local disk
- `push_template(local_path, templates_dir)` — uploads one template JSON to R2 under `templates/<relative-path>`
- `delete_template(key)` — deletes one object from R2
- `upload_export(local_path) -> str` — uploads export file to `exports/<filename>`, deletes local file, returns presigned URL (1-hour TTL)

### Changes to `app.py`

**Startup:** Call `storage.sync_templates_from_r2(TEMPLATES_DIR)` before the first request (using `@app.before_request` with a once-flag or Flask's `with app.app_context()`).

**Template endpoints** (`POST /api/templates`, `PATCH /api/templates/<name>`, `DELETE /api/templates/<name>` and their top5 equivalents): After local file operation succeeds, call `push_template` or `delete_template` in a background thread.

**Export endpoints** (all three: `/api/export`, `/api/top5/export`, `/api/express-export`): After `export_video()` / `export_top5()` returns a local path, call `storage.upload_export(path)` to get a presigned URL. The `done` SSE event becomes:

```json
{"type": "done", "filename": "output.mp4", "download_url": "<presigned-url>"}
```

The local export file is deleted after upload.

### Frontend change

The frontend currently constructs a download link from `output_path` or calls `/api/exports/<filename>`. It needs to use `download_url` from the `done` event directly instead. This is a small change — `download_url` is already a complete URL.

## Error Handling

| Failure | Behavior |
|---|---|
| R2 sync fails on startup | Log warning, continue with whatever templates exist locally |
| Template R2 push fails | Log warning, do not fail the API response (local write already succeeded) |
| Export R2 upload fails | Send `{"type": "error", "message": "export succeeded but upload failed: ..."}` — user knows video was generated |
| Presigned URL expires (1hr) | User must re-export; no retry mechanism needed |

## Render Deployment Config

### `build.sh`
```bash
#!/usr/bin/env bash
set -e
apt-get install -y ffmpeg
pip install -r requirements.txt
```

### `render.yaml`
```yaml
services:
  - type: web
    name: autoclipper
    env: python
    buildCommand: bash build.sh
    startCommand: gunicorn app:app --workers 2 --threads 4 --timeout 300
    envVars:
      - key: R2_ENDPOINT_URL
        sync: false
      - key: R2_ACCESS_KEY_ID
        sync: false
      - key: R2_SECRET_ACCESS_KEY
        sync: false
      - key: R2_BUCKET_NAME
        sync: false
```

Workers/threads: 2 workers × 4 threads gives concurrency for SSE streams without exceeding Render free tier memory. Timeout 300s covers long ffmpeg exports.

### `requirements.txt` additions
- `boto3>=1.34`
- `gunicorn>=21.0`

## R2 Bucket Setup (manual, one-time)

1. Create bucket in Cloudflare dashboard
2. Create API token with Object Read & Write permissions scoped to that bucket
3. Note the S3-compatible endpoint URL (`https://<account-id>.r2.cloudflarestorage.com`)
4. Add all four values as environment variables in Render dashboard

No public bucket access needed — exports are served via presigned URLs.
