from unittest.mock import patch

import boto3
import pytest

from app.core.config import Settings
from app.services.storage import StorageService


def test_storage_a_local_explicit_credentials():
    """Test A: Local explicit credentials configure MinIO client with those credentials."""
    with patch("app.services.storage.boto3.client") as mock_client:
        service = StorageService(
            endpoint_url="http://localhost:9100",
            public_endpoint_url="http://localhost:9100",
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
            region_name="us-east-1",
            bucket_name="ramaiahmart-media",
        )

        assert service.endpoint_url == "http://localhost:9100"
        assert service.aws_access_key_id == "minioadmin"
        assert service.aws_secret_access_key == "minioadmin"

        # Client was initialized with explicit MinIO parameters
        mock_client.assert_called_once()
        _, kwargs = mock_client.call_args
        assert kwargs["endpoint_url"] == "http://localhost:9100"
        assert kwargs["aws_access_key_id"] == "minioadmin"
        assert kwargs["aws_secret_access_key"] == "minioadmin"
        assert kwargs["region_name"] == "us-east-1"


def test_storage_b_production_iam_role_mode():
    """Test B: Production IAM role mode constructs client without supplying access keys or endpoint URL."""
    # Use real boto3 client creation via spy to verify construction succeeds without network calls
    with patch("app.services.storage.boto3.client", wraps=boto3.client) as spy_client:
        service = StorageService(
            endpoint_url=None,
            public_endpoint_url=None,
            aws_access_key_id=None,
            aws_secret_access_key=None,
            region_name="ap-south-1",
            bucket_name="ramaiahmart-media-production",
        )

        assert service.endpoint_url is None
        assert service.public_endpoint_url is None
        assert service.aws_access_key_id is None
        assert service.aws_secret_access_key is None
        assert service.region_name == "ap-south-1"

        # Verify boto3 was called without credentials and without endpoint_url
        spy_client.assert_called_once()
        _, kwargs = spy_client.call_args
        assert "aws_access_key_id" not in kwargs
        assert "aws_secret_access_key" not in kwargs
        assert "endpoint_url" not in kwargs
        assert kwargs["region_name"] == "ap-south-1"

        # Both internal client and public client share the same instance when endpoints match
        assert service.client is service.public_client


def test_storage_c_production_rejects_development_credentials():
    """Test C: Production configuration rejects default minioadmin credentials."""
    with pytest.raises(
        ValueError, match="Cannot use default development minioadmin credentials"
    ):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a" * 32,
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg://prod:pass@db.example.com:5432/db",
            AWS_ACCESS_KEY_ID="minioadmin",
            AWS_SECRET_ACCESS_KEY="minioadmin",
            S3_BUCKET_NAME="ramaiahmart-media-production",
            AWS_REGION="ap-south-1",
        )


def test_storage_d_production_accepts_absent_credentials():
    """Test D: Production accepts absent AWS credentials (enabling EC2 IAM role usage)."""
    # Explicitly None
    settings_none = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="a" * 32,
        DEBUG=False,
        DATABASE_URL="postgresql+psycopg://prod:pass@db.example.com:5432/db",
        AWS_ACCESS_KEY_ID=None,
        AWS_SECRET_ACCESS_KEY=None,
        S3_ENDPOINT_URL=None,
        S3_PUBLIC_ENDPOINT_URL=None,
        AWS_REGION="ap-south-1",
        S3_BUCKET_NAME="ramaiahmart-media-production",
    )
    assert settings_none.APP_ENV == "production"
    assert settings_none.AWS_ACCESS_KEY_ID is None
    assert settings_none.AWS_SECRET_ACCESS_KEY is None
    assert settings_none.S3_ENDPOINT_URL is None

    # Omitted entirely (relying on default None)
    settings_default = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="a" * 32,
        DEBUG=False,
        DATABASE_URL="postgresql+psycopg://prod:pass@db.example.com:5432/db",
        AWS_REGION="ap-south-1",
        S3_BUCKET_NAME="ramaiahmart-media-production",
    )
    assert settings_default.APP_ENV == "production"
    assert settings_default.AWS_ACCESS_KEY_ID is None
    assert settings_default.AWS_SECRET_ACCESS_KEY is None


def test_storage_empty_string_normalization():
    """Empty strings for endpoint URL and credentials normalize to None so boto3 credential chain applies."""
    with patch("app.services.storage.boto3.client") as mock_client:
        service = StorageService(
            endpoint_url="",
            public_endpoint_url="",
            aws_access_key_id="",
            aws_secret_access_key="",
            region_name="ap-south-1",
        )

        assert service.endpoint_url is None
        assert service.public_endpoint_url is None
        assert service.aws_access_key_id is None
        assert service.aws_secret_access_key is None

        mock_client.assert_called_once()
        _, kwargs = mock_client.call_args
        assert "aws_access_key_id" not in kwargs
        assert "aws_secret_access_key" not in kwargs
        assert "endpoint_url" not in kwargs
        assert kwargs["region_name"] == "ap-south-1"


def test_storage_presigned_urls_with_public_endpoint():
    """Presigned URLs use public endpoint when distinct public endpoint is configured."""
    with patch("app.services.storage.boto3.client") as mock_client:
        mock_internal = mock_client.return_value
        service = StorageService(
            endpoint_url="http://internal-minio:9000",
            public_endpoint_url="https://cdn.example.com",
            aws_access_key_id="customkey",
            aws_secret_access_key="customsecret",
            region_name="us-east-1",
        )

        assert mock_client.call_count == 2
        # Verify internal vs public client construction calls
        first_call_kwargs = mock_client.call_args_list[0][1]
        second_call_kwargs = mock_client.call_args_list[1][1]
        assert first_call_kwargs["endpoint_url"] == "http://internal-minio:9000"
        assert second_call_kwargs["endpoint_url"] == "https://cdn.example.com"
