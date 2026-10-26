from __future__ import annotations
import os
from datetime import datetime, timezone


def upload_evidence(payload: bytes, key: str) -> tuple[bool, str]:
    """Upload a report to S3. Returns a friendly status instead of hiding config errors."""
    bucket = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-1")
    if not bucket:
        return False, "S3_BUCKET is not configured. No upload was attempted."
    try:
        import boto3
        client = boto3.client("s3", region_name=region)
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=payload,
            ContentType="application/json",
            ServerSideEncryption="AES256",
            Metadata={"uploaded-at-utc": datetime.now(timezone.utc).isoformat()},
        )
        return True, f"Report archived to s3://{bucket}/{key} (server-side encryption requested)."
    except Exception as exc:
        return False, f"S3 upload failed: {type(exc).__name__}: {exc}"
