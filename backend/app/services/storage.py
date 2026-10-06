import logging
import uuid
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

MIME_EXTENSION_MAP: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def detect_image_format(data: bytes) -> str | None:
    """Determine authentic image MIME type from raw magic bytes signature.

    Returns:
        Canonical MIME type ('image/jpeg', 'image/png', 'image/webp') or None if unrecognized.
    """
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class StorageService:
    """Storage service abstraction supporting both AWS S3 and MinIO."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        public_endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str | None = None,
        bucket_name: str | None = None,
        presigned_expiration: int | None = None,
    ) -> None:
        raw_endpoint = endpoint_url if endpoint_url is not None else settings.S3_ENDPOINT_URL
        self.endpoint_url = raw_endpoint.strip() if (raw_endpoint and raw_endpoint.strip()) else None

        raw_public_endpoint = (
            public_endpoint_url
            if public_endpoint_url is not None
            else settings.S3_PUBLIC_ENDPOINT_URL
        )
        if raw_public_endpoint and raw_public_endpoint.strip():
            self.public_endpoint_url = raw_public_endpoint.strip()
        else:
            self.public_endpoint_url = self.endpoint_url

        raw_access_key = (
            aws_access_key_id
            if aws_access_key_id is not None
            else settings.AWS_ACCESS_KEY_ID
        )
        self.aws_access_key_id = (
            raw_access_key.strip() if (raw_access_key and raw_access_key.strip()) else None
        )

        raw_secret_key = (
            aws_secret_access_key
            if aws_secret_access_key is not None
            else settings.AWS_SECRET_ACCESS_KEY
        )
        self.aws_secret_access_key = (
            raw_secret_key.strip() if (raw_secret_key and raw_secret_key.strip()) else None
        )

        raw_region = region_name if region_name is not None else settings.AWS_REGION
        self.region_name = (
            raw_region.strip() if (raw_region and raw_region.strip()) else None
        )

        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.presigned_expiration = (
            presigned_expiration or settings.STORAGE_PRESIGNED_EXPIRATION_SECONDS
        )

        # Internal client for backend operations (delete, head, create bucket)
        self._client: Any = self._create_client(self.endpoint_url)

        # Public client for generating presigned URLs reachable by browsers
        if self.public_endpoint_url != self.endpoint_url:
            self._public_client: Any = self._create_client(self.public_endpoint_url)
        else:
            self._public_client = self._client

    def _create_client(self, endpoint_url: str | None) -> Any:
        """Construct a boto3 S3 client with only the explicitly provided options."""
        client_kwargs: dict[str, Any] = {
            "config": Config(signature_version="s3v4"),
        }
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if self.region_name:
            client_kwargs["region_name"] = self.region_name
        if self.aws_access_key_id and self.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = self.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key

        return boto3.client("s3", **client_kwargs)

    @property
    def client(self) -> Any:
        return self._client

    @property
    def public_client(self) -> Any:
        return self._public_client

    def build_safe_storage_key(self, post_id: uuid.UUID, content_type: str) -> str:
        """Generate safe, collision-resistant storage key namespaced by post ID.

        Client-supplied filenames are ignored to prevent path traversal and arbitrary keys.
        """
        ext = MIME_EXTENSION_MAP.get(content_type.lower().strip(), ".jpg")
        return f"posts/{post_id}/{uuid.uuid4()}{ext}"

    def generate_upload_url(
        self, storage_key: str, content_type: str, expires_in: int | None = None
    ) -> str:
        """Generate a presigned PUT upload URL for direct browser-to-storage transfer."""
        expiry = expires_in or self.presigned_expiration
        params = {
            "Bucket": self.bucket_name,
            "Key": storage_key,
            "ContentType": content_type,
        }
        try:
            url: str = self.public_client.generate_presigned_url(
                ClientMethod="put_object",
                Params=params,
                ExpiresIn=expiry,
            )
            return url
        except Exception as e:
            logger.warning("Could not generate presigned upload URL for %s: %s", storage_key, e)
            if self.public_endpoint_url:
                return f"{self.public_endpoint_url.rstrip('/')}/{self.bucket_name}/{storage_key}"
            return f"https://{self.bucket_name}.s3.{self.region_name or 'amazonaws'}.com/{storage_key}"

    def generate_download_url(self, storage_key: str, expires_in: int | None = None) -> str:
        """Generate a presigned GET download URL for reading an object."""
        expiry = expires_in or self.presigned_expiration
        params = {
            "Bucket": self.bucket_name,
            "Key": storage_key,
        }
        try:
            url: str = self.public_client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=expiry,
            )
            return url
        except Exception as e:
            logger.warning("Could not generate presigned download URL for %s: %s", storage_key, e)
            if self.public_endpoint_url:
                return f"{self.public_endpoint_url.rstrip('/')}/{self.bucket_name}/{storage_key}"
            return f"https://{self.bucket_name}.s3.{self.region_name or 'amazonaws'}.com/{storage_key}"

    def object_exists(self, storage_key: str) -> bool:
        """Verify if an object exists in storage via HEAD request."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return False
            logger.warning("Error checking object existence for %s: %s", storage_key, e)
            return False

    def get_object_metadata(self, storage_key: str) -> dict[str, Any] | None:
        """Retrieve object metadata via HEAD request."""
        try:
            res = self.client.head_object(Bucket=self.bucket_name, Key=storage_key)
            return {
                "content_length": int(res.get("ContentLength", 0)),
                "content_type": str(res.get("ContentType", "")),
            }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return None
            logger.warning("Error getting object metadata for %s: %s", storage_key, e)
            return None

    def get_object_header(self, storage_key: str, max_bytes: int = 512) -> bytes:
        """Read first N bytes of an object via HTTP Range request without buffering full file."""
        try:
            res = self.client.get_object(
                Bucket=self.bucket_name,
                Key=storage_key,
                Range=f"bytes=0-{max_bytes - 1}",
            )
            body: bytes = res["Body"].read(max_bytes)
            return body
        except ClientError as e:
            logger.warning("Error reading object header for %s: %s", storage_key, e)
            return b""

    def delete_object(self, storage_key: str) -> None:
        """Delete an object from storage. Safe if object is already missing."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=storage_key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                logger.info("Storage object already missing: %s", storage_key)
                return
            logger.error("Failed to delete storage object %s: %s", storage_key, e)
            raise

    def ensure_bucket_exists(self) -> None:
        """Ensure target bucket exists in local/test storage."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                if not self.region_name or self.region_name == "us-east-1":
                    self.client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": self.region_name},
                    )
            except ClientError as e:
                logger.warning("Could not auto-create bucket %s: %s", self.bucket_name, e)


storage_service = StorageService()
