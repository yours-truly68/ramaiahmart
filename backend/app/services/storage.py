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
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.public_endpoint_url = (
            public_endpoint_url or settings.S3_PUBLIC_ENDPOINT_URL or self.endpoint_url
        )
        self.aws_access_key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY
        self.region_name = region_name or settings.AWS_REGION
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.presigned_expiration = (
            presigned_expiration or settings.STORAGE_PRESIGNED_EXPIRATION_SECONDS
        )

        # Internal client for backend operations (delete, head, create bucket)
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
            config=Config(signature_version="s3v4"),
        )

        # Public client for generating presigned URLs reachable by browsers
        if self.public_endpoint_url != self.endpoint_url:
            self._public_client: Any = boto3.client(
                "s3",
                endpoint_url=self.public_endpoint_url,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name,
                config=Config(signature_version="s3v4"),
            )
        else:
            self._public_client = self._client

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
        url: str = self.public_client.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=expiry,
        )
        return url

    def generate_download_url(self, storage_key: str, expires_in: int | None = None) -> str:
        """Generate a presigned GET download URL for reading an object."""
        expiry = expires_in or self.presigned_expiration
        params = {
            "Bucket": self.bucket_name,
            "Key": storage_key,
        }
        url: str = self.public_client.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=expiry,
        )
        return url

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

    def delete_object(self, storage_key: str) -> None:
        """Delete an object from storage."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=storage_key)
        except ClientError as e:
            logger.error("Failed to delete storage object %s: %s", storage_key, e)
            raise

    def ensure_bucket_exists(self) -> None:
        """Ensure target bucket exists in local/test storage."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                if self.region_name == "us-east-1":
                    self.client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": self.region_name},
                    )
            except ClientError as e:
                logger.warning("Could not auto-create bucket %s: %s", self.bucket_name, e)


storage_service = StorageService()
