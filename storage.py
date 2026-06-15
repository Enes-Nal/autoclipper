import os
import logging
from pathlib import Path

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

_ENDPOINT = os.environ.get("R2_ENDPOINT_URL", "")
_KEY      = os.environ.get("R2_ACCESS_KEY_ID", "")
_SECRET   = os.environ.get("R2_SECRET_ACCESS_KEY", "")
_BUCKET   = os.environ.get("R2_BUCKET_NAME", "")

_client = None
if _ENDPOINT and _KEY and _SECRET and _BUCKET:
    _client = boto3.client(
        "s3",
        endpoint_url=_ENDPOINT,
        aws_access_key_id=_KEY,
        aws_secret_access_key=_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def is_configured() -> bool:
    return _client is not None


def sync_templates_from_r2(templates_dir: Path) -> None:
    """Download any templates present in R2 but missing locally."""
    if not is_configured():
        return
    try:
        resp = _client.list_objects_v2(Bucket=_BUCKET, Prefix="templates/")
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            filename = Path(key).name
            if not filename:
                continue
            local_path = templates_dir / filename
            if not local_path.exists():
                templates_dir.mkdir(parents=True, exist_ok=True)
                _client.download_file(_BUCKET, key, str(local_path))
                logger.info("synced template from R2: %s", key)
    except Exception:
        logger.warning("R2 template sync failed", exc_info=True)


def push_template(local_path: Path, templates_dir: Path) -> None:
    """Upload a template file to R2. Silent no-op if R2 not configured."""
    if not is_configured():
        return
    try:
        key = f"templates/{local_path.relative_to(templates_dir).as_posix()}"
        _client.upload_file(str(local_path), _BUCKET, key)
        logger.info("pushed template to R2: %s", key)
    except Exception:
        logger.warning("R2 template push failed: %s", local_path, exc_info=True)


def delete_template(key: str) -> None:
    """Delete a template object from R2. Silent no-op if R2 not configured."""
    if not is_configured():
        return
    try:
        _client.delete_object(Bucket=_BUCKET, Key=key)
        logger.info("deleted template from R2: %s", key)
    except Exception:
        logger.warning("R2 template delete failed: %s", key, exc_info=True)


def upload_export(local_path: Path) -> str | None:
    """Upload export file to R2, delete local copy, return 1-hour presigned URL.

    Returns None if R2 is not configured (caller serves local file instead).
    """
    if not is_configured():
        return None
    key = f"exports/{local_path.name}"
    try:
        _client.upload_file(str(local_path), _BUCKET, key)
        url = _client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _BUCKET, "Key": key},
            ExpiresIn=3600,
        )
        local_path.unlink()
        return url
    except Exception:
        logger.error("R2 export upload failed: %s", local_path, exc_info=True)
        raise
