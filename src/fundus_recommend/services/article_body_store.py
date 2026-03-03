from __future__ import annotations

import hashlib
import logging
from typing import Any

from fundus_recommend.config import settings

try:  # pragma: no cover - import guard for local environments before dependency install
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover
    boto3 = None
    BotoConfig = None
    BotoCoreError = Exception
    ClientError = Exception

logger = logging.getLogger(__name__)


class BodyStoreError(RuntimeError):
    """Raised when body storage operations fail."""


class BodyNotFoundError(BodyStoreError):
    """Raised when a body key is not found in object storage."""


class BodyStoreNotConfiguredError(BodyStoreError):
    """Raised when required R2 configuration is missing."""


_client: Any | None = None


def _resolve_endpoint() -> str:
    if settings.r2_endpoint:
        return settings.r2_endpoint
    if not settings.r2_account_id:
        raise BodyStoreNotConfiguredError("R2_ACCOUNT_ID is required when R2_ENDPOINT is not set")
    return f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"


def _validate_configuration() -> None:
    missing: list[str] = []
    if not settings.r2_access_key_id:
        missing.append("R2_ACCESS_KEY_ID")
    if not settings.r2_secret_access_key:
        missing.append("R2_SECRET_ACCESS_KEY")
    if not settings.r2_bucket:
        missing.append("R2_BUCKET")
    if missing:
        raise BodyStoreNotConfiguredError(f"Missing required R2 configuration: {', '.join(missing)}")


def _get_client() -> Any:
    global _client
    if _client is not None:
        return _client

    if boto3 is None or BotoConfig is None:
        raise BodyStoreError("boto3 is required for Cloudflare R2 storage")

    _validate_configuration()
    _client = boto3.client(
        "s3",
        endpoint_url=_resolve_endpoint(),
        region_name=settings.r2_region,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=BotoConfig(
            signature_version="s3v4",
            connect_timeout=settings.r2_timeout_seconds,
            read_timeout=settings.r2_timeout_seconds,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
    return _client


def build_body_key(article_id: int, url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return f"articles/{article_id}/{digest}.txt"


def put_body(key: str, body: str) -> None:
    client = _get_client()
    try:
        client.put_object(
            Bucket=settings.r2_bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("article_body_put_failed key=%s bucket=%s error=%s", key, settings.r2_bucket, exc)
        raise BodyStoreError("Failed to store article body in R2") from exc


def get_body(key: str) -> str:
    client = _get_client()
    try:
        response = client.get_object(Bucket=settings.r2_bucket, Key=key)
    except ClientError as exc:
        response_payload = getattr(exc, "response", None)
        if not isinstance(response_payload, dict):
            logger.exception("article_body_get_failed key=%s bucket=%s error=%s", key, settings.r2_bucket, exc)
            raise BodyStoreError("Failed to read article body from R2") from exc

        error_code = response_payload.get("Error", {}).get("Code")
        if error_code in {"NoSuchKey", "404", "NotFound"}:
            raise BodyNotFoundError(f"Body key not found: {key}") from exc
        logger.exception("article_body_get_failed key=%s bucket=%s error=%s", key, settings.r2_bucket, exc)
        raise BodyStoreError("Failed to read article body from R2") from exc
    except BotoCoreError as exc:
        logger.exception("article_body_get_failed key=%s bucket=%s error=%s", key, settings.r2_bucket, exc)
        raise BodyStoreError("Failed to read article body from R2") from exc

    payload = response["Body"].read()
    if isinstance(payload, str):
        return payload
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        logger.exception("article_body_decode_failed key=%s bucket=%s", key, settings.r2_bucket)
        raise BodyStoreError("Stored article body is not valid UTF-8") from exc
