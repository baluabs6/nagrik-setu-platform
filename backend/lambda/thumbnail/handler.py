"""
Triggered by S3 ObjectCreated events under the `issue-attachments/` prefix.
Generates a 320px-wide thumbnail and writes it back to the same bucket
under `issue-attachments-thumbnails/`, mirroring the original key name.

Kept dependency-light (Pillow only, via a Lambda layer — see
infra/terraform/aws/lambda.tf) since this runs on every single upload.
"""
import io
import os
import logging

import boto3
from PIL import Image

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

THUMBNAIL_WIDTH = int(os.environ.get("THUMBNAIL_WIDTH", "320"))
SOURCE_PREFIX = "issue-attachments/"
THUMBNAIL_PREFIX = "issue-attachments-thumbnails/"


def handler(event, context):
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        if not key.startswith(SOURCE_PREFIX):
            continue  # ignore anything outside the expected prefix
        if key.startswith(THUMBNAIL_PREFIX):
            continue  # safety: never re-trigger on our own output

        try:
            _make_thumbnail(bucket, key)
        except Exception:
            # Log and move on rather than fail the whole batch — a missing
            # thumbnail should never block the underlying upload from
            # being usable; Home.tsx falls back gracefully if the
            # thumbnail key never appears.
            logger.exception("Thumbnail generation failed for s3://%s/%s", bucket, key)

    return {"statusCode": 200}


def _make_thumbnail(bucket: str, key: str) -> None:
    obj = s3.get_object(Bucket=bucket, Key=key)
    image = Image.open(io.BytesIO(obj["Body"].read()))
    image = image.convert("RGB") if image.mode in ("P", "RGBA") else image

    # A tall second bound (10x the width) means the width is effectively
    # the only real constraint, while still letting Pillow do its own
    # aspect-preserving math in one step instead of pre-computing a ratio
    # ourselves and rounding twice.
    image.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_WIDTH * 10))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82)
    buffer.seek(0)

    thumbnail_key = key.replace(SOURCE_PREFIX, THUMBNAIL_PREFIX, 1)
    s3.put_object(
        Bucket=bucket,
        Key=thumbnail_key,
        Body=buffer,
        ContentType="image/jpeg",
    )
    logger.info("Wrote thumbnail s3://%s/%s", bucket, thumbnail_key)
