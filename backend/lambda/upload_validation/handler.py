"""
Triggered by S3 ObjectCreated events under `issue-attachments/`, in
parallel with the thumbnail Lambda (backend/lambda/thumbnail/).

The presigned-PUT upload flow in apps/issues/views.py.presign_upload only
checks a client-declared `Content-Type` string — nothing stops a browser
(or a script bypassing the browser entirely) from PUTting arbitrary bytes
under an `image/jpeg` content type. This Lambda is the actual enforcement
point:

  1. Sniff the real file type from the magic bytes (Pillow's `Image.open`
     raising is a very effective "this isn't really an image" signal).
  2. Reject anything over the declared size limit or not JPEG/PNG/WebP.
  3. For genuine images, re-save them stripped of all metadata (Pillow's
     re-encode drops EXIF by default) so GPS coordinates embedded in a
     citizen's phone photo are never served back publicly.
  4. On success, PATCH the owning Issue's `attachment_verified` flag via
     the Django API so `Issue.attachment_url()` starts returning a link.
  5. On failure, delete the object — better to lose one photo than serve
     unverified/attacker-controlled content from the bucket.

Dependency-light (Pillow only, via the same Lambda layer as the thumbnail
function — see infra/terraform/aws/upload-validation.tf).
"""
import io
import json
import logging
import os
import urllib.request

import boto3
from PIL import Image

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

SOURCE_PREFIX = "issue-attachments/"
THUMBNAIL_PREFIX = "issue-attachments-thumbnails/"
MAX_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

# Internal-only callback so this Lambda can flip attachment_verified;
# never exposed to citizens. Configure as a Lambda environment variable
# pointing at a private/VPC-internal endpoint, with its own service token
# (kept in Vault/Secrets Manager, not hardcoded).
BACKEND_INTERNAL_URL = os.environ.get("BACKEND_INTERNAL_URL", "")
BACKEND_INTERNAL_TOKEN = os.environ.get("BACKEND_INTERNAL_TOKEN", "")


def handler(event, context):
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        if not key.startswith(SOURCE_PREFIX) or key.startswith(THUMBNAIL_PREFIX):
            continue

        try:
            _validate_and_clean(bucket, key)
        except _RejectUpload as exc:
            logger.warning("Rejected upload s3://%s/%s: %s", bucket, key, exc)
            s3.delete_object(Bucket=bucket, Key=key)
        except Exception:
            # Unexpected failure: fail closed by leaving attachment_verified
            # False rather than risk silently approving something unchecked.
            logger.exception("Validation error for s3://%s/%s; leaving unverified", bucket, key)

    return {"statusCode": 200}


class _RejectUpload(Exception):
    pass


def _validate_and_clean(bucket: str, key: str) -> None:
    head = s3.head_object(Bucket=bucket, Key=key)
    if head["ContentLength"] > MAX_BYTES:
        raise _RejectUpload(f"{head['ContentLength']} bytes exceeds {MAX_BYTES} limit")

    obj = s3.get_object(Bucket=bucket, Key=key)
    raw = obj["Body"].read()

    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()  # raises if the bytes aren't a real, parseable image
        image = Image.open(io.BytesIO(raw))  # re-open: verify() consumes the parser
    except Exception as exc:
        raise _RejectUpload(f"not a valid image: {exc}") from exc

    if image.format not in ALLOWED_FORMATS:
        raise _RejectUpload(f"unsupported format {image.format}")

    # Re-encoding through Pillow without carrying `exif=` forward drops all
    # metadata, including GPS EXIF tags a phone camera embeds by default.
    if image.mode in ("P", "RGBA") and image.format != "PNG":
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format=image.format)
    buffer.seek(0)

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer,
        ContentType=f"image/{image.format.lower()}",
    )
    logger.info("Verified and stripped metadata for s3://%s/%s", bucket, key)
    _mark_verified(key)


def _mark_verified(attachment_key: str) -> None:
    if not BACKEND_INTERNAL_URL:
        logger.info("BACKEND_INTERNAL_URL not set; skipping attachment_verified callback")
        return
    try:
        body = json.dumps({"attachment_key": attachment_key}).encode("utf-8")
        request = urllib.request.Request(
            f"{BACKEND_INTERNAL_URL}/api/v1/internal/mark-attachment-verified/",
            data=body,
            headers={
                "content-type": "application/json",
                "x-internal-token": BACKEND_INTERNAL_TOKEN,
            },
            method="POST",
        )
        urllib.request.urlopen(request, timeout=5)
    except Exception:
        logger.exception("Failed to notify backend that %s is verified", attachment_key)
