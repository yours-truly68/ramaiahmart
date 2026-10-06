import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_storage_service
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.category import Category
from app.models.post import Post, PostImage, PostStatus, PostType
from app.models.user import User


@pytest.fixture
def mock_storage_service():
    """Mock storage service to simulate MinIO / S3 operations."""
    mock = MagicMock()
    mock.bucket_name = "ramaiahmart-media"
    mock.public_endpoint_url = "http://localhost:9100"
    mock.presigned_expiration = 900

    def mock_build_key(post_id: uuid.UUID, content_type: str) -> str:
        ext = ".jpg" if "jpeg" in content_type or "jpg" in content_type else ".png"
        return f"posts/{post_id}/{uuid.uuid4()}{ext}"

    def mock_upload_url(storage_key: str, content_type: str, expires_in: int | None = None) -> str:
        return f"http://localhost:9100/ramaiahmart-media/{storage_key}?X-Amz-Signature=test"

    def mock_download_url(storage_key: str, expires_in: int | None = None) -> str:
        return f"http://localhost:9100/ramaiahmart-media/{storage_key}"

    mock.build_safe_storage_key.side_effect = mock_build_key
    mock.generate_upload_url.side_effect = mock_upload_url
    mock.generate_download_url.side_effect = mock_download_url

    def mock_get_header(storage_key: str, max_bytes: int = 512) -> bytes:
        if storage_key.endswith(".png"):
            return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        if storage_key.endswith(".webp"):
            return b"RIFF\x00\x00\x00\x00WEBPVP8 "
        return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"

    mock.object_exists.return_value = True
    mock.get_object_metadata.return_value = {
        "content_length": 1024,
        "content_type": "image/jpeg",
    }
    mock.get_object_header.side_effect = mock_get_header
    mock.delete_object.return_value = None

    return mock


@pytest.fixture
def test_setup():
    """Setup test users, category, and posts in database."""
    db = SessionLocal()
    try:
        user_a = User(
            email=f"media_user_a_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Media Student A",
            hashed_password="test_hashed_password_123",
            university_verified=True,
            is_active=True,
        )
        user_b = User(
            email=f"media_user_b_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Media Student B",
            hashed_password="test_hashed_password_123",
            university_verified=True,
            is_active=True,
        )
        category = Category(
            name=f"Electronics {uuid.uuid4().hex[:6]}",
            slug=f"electronics-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db.add_all([user_a, user_b, category])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        db.refresh(category)

        post = Post(
            author_id=user_a.id,
            category_id=category.id,
            type=PostType.OFFER,
            title="Scientific Calculator fx-991CW",
            description="Used for 1 semester, perfectly functional with cover.",
            price=Decimal("850.00"),
            price_unit="total",
            status=PostStatus.DRAFT,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        token_a = create_access_token(subject=str(user_a.id))
        token_b = create_access_token(subject=str(user_b.id))

        yield {
            "user_a": user_a,
            "user_b": user_b,
            "token_a": token_a,
            "token_b": token_b,
            "category": category,
            "post": post,
        }
    finally:
        db.close()


@pytest.mark.asyncio
async def test_upload_url_generation(test_setup, mock_storage_service):
    """Test generating a presigned PUT upload URL with safe storage key."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {test_setup['token_a']}"}
            payload = {
                "post_id": str(test_setup["post"].id),
                "content_type": "image/jpeg",
                "file_size": 1024 * 500,  # 500 KB
            }
            res = await client.post("/api/v1/media/upload-url", json=payload, headers=headers)
            assert res.status_code == 200, res.text
            data = res.json()
            assert "upload_url" in data
            assert "storage_key" in data
            assert data["expires_in"] == 900
            assert data["storage_key"].startswith(f"posts/{test_setup['post'].id}/")
            assert data["storage_key"].endswith(".jpg")
    finally:
        app.dependency_overrides.pop(get_storage_service, None)


@pytest.mark.asyncio
async def test_upload_url_invalid_mime_type(test_setup, mock_storage_service):
    """Test that unsupported media MIME types are rejected."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {test_setup['token_a']}"}
            payload = {
                "post_id": str(test_setup["post"].id),
                "content_type": "application/pdf",
                "file_size": 1024 * 100,
            }
            res = await client.post("/api/v1/media/upload-url", json=payload, headers=headers)
            assert res.status_code == 422
            assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_storage_service, None)


@pytest.mark.asyncio
async def test_upload_url_oversized_file(test_setup, mock_storage_service):
    """Test that file sizes exceeding maximum allowed limit are rejected."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {test_setup['token_a']}"}
            payload = {
                "post_id": str(test_setup["post"].id),
                "content_type": "image/png",
                "file_size": 15 * 1024 * 1024,  # 15 MB > 10 MB limit
            }
            res = await client.post("/api/v1/media/upload-url", json=payload, headers=headers)
            assert res.status_code == 422
            assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_storage_service, None)


@pytest.mark.asyncio
async def test_media_unauthorized_access(test_setup, mock_storage_service):
    """Test unauthorized requests and cross-user tampering protection."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Unauthenticated request
            res = await client.post(
                "/api/v1/media/upload-url",
                json={
                    "post_id": str(test_setup["post"].id),
                    "content_type": "image/jpeg",
                    "file_size": 1024,
                },
            )
            assert res.status_code == 401

            # 2. User B attempting to request upload URL for User A's post
            headers_b = {"Authorization": f"Bearer {test_setup['token_b']}"}
            res_tamper = await client.post(
                "/api/v1/media/upload-url",
                json={
                    "post_id": str(test_setup["post"].id),
                    "content_type": "image/jpeg",
                    "file_size": 1024,
                },
                headers=headers_b,
            )
            assert res_tamper.status_code == 403
            assert res_tamper.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"

            # 3. User B attempting to complete upload on User A's post
            res_complete_tamper = await client.post(
                "/api/v1/media/complete",
                json={
                    "post_id": str(test_setup["post"].id),
                    "storage_key": f"posts/{test_setup['post'].id}/test.jpg",
                },
                headers=headers_b,
            )
            assert res_complete_tamper.status_code == 403
            assert res_complete_tamper.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"
    finally:
        app.dependency_overrides.pop(get_storage_service, None)


@pytest.mark.asyncio
async def test_completing_upload_and_key_validation(test_setup, mock_storage_service):
    """Test finalizing direct upload with key validation and object existence checks."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers_a = {"Authorization": f"Bearer {test_setup['token_a']}"}
            post_id = test_setup["post"].id

            # 1. Invalid storage key prefix (arbitrary bucket/key access prevention)
            res_bad_key = await client.post(
                "/api/v1/media/complete",
                json={
                    "post_id": str(post_id),
                    "storage_key": "arbitrary_bucket/evil.jpg",
                },
                headers=headers_a,
            )
            assert res_bad_key.status_code == 400
            assert res_bad_key.json()["error"]["code"] == "INVALID_STORAGE_KEY"

            # 2. Object does not exist in storage
            mock_storage_service.object_exists.return_value = False
            res_not_found = await client.post(
                "/api/v1/media/complete",
                json={
                    "post_id": str(post_id),
                    "storage_key": f"posts/{post_id}/missing.jpg",
                },
                headers=headers_a,
            )
            assert res_not_found.status_code == 400
            assert res_not_found.json()["error"]["code"] == "OBJECT_NOT_FOUND"

            # 3. Successful completion when object exists
            mock_storage_service.object_exists.return_value = True
            valid_key_1 = f"posts/{post_id}/{uuid.uuid4()}.jpg"
            res_ok = await client.post(
                "/api/v1/media/complete",
                json={
                    "post_id": str(post_id),
                    "storage_key": valid_key_1,
                },
                headers=headers_a,
            )
            assert res_ok.status_code == 201, res_ok.text
            media_1 = res_ok.json()
            assert media_1["storage_key"] == valid_key_1
            assert media_1["position"] == 0
            assert media_1["post_id"] == str(post_id)

            # 4. Duplicate complete registration rejected
            res_dup = await client.post(
                "/api/v1/media/complete",
                json={
                    "post_id": str(post_id),
                    "storage_key": valid_key_1,
                },
                headers=headers_a,
            )
            assert res_dup.status_code == 400
            assert res_dup.json()["error"]["code"] == "MEDIA_ALREADY_ATTACHED"

            # 5. Second upload auto-increments position
            valid_key_2 = f"posts/{post_id}/{uuid.uuid4()}.png"
            res_ok_2 = await client.post(
                "/api/v1/media/complete",
                json={
                    "post_id": str(post_id),
                    "storage_key": valid_key_2,
                },
                headers=headers_a,
            )
            assert res_ok_2.status_code == 201
            assert res_ok_2.json()["position"] == 1

            # 6. Verify post details include attached media in order
            post_res = await client.get(f"/api/v1/posts/{post_id}", headers=headers_a)
            assert post_res.status_code == 200
            post_data = post_res.json()
            assert len(post_data["images"]) == 2
            assert post_data["images"][0]["position"] == 0
            assert post_data["images"][1]["position"] == 1
    finally:
        app.dependency_overrides.pop(get_storage_service, None)


@pytest.mark.asyncio
async def test_deleting_owned_media_and_unauthorized_deletion(test_setup, mock_storage_service):
    """Test deleting owned media and preventing unauthorized deletion by other users."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    try:
        # Create a media item directly in database
        db = SessionLocal()
        media = PostImage(
            post_id=test_setup["post"].id,
            storage_key=f"posts/{test_setup['post'].id}/{uuid.uuid4()}.jpg",
            public_url="http://localhost:9100/test.jpg",
            position=0,
        )
        db.add(media)
        db.commit()
        db.refresh(media)
        media_id = media.id
        db.close()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers_b = {"Authorization": f"Bearer {test_setup['token_b']}"}
            headers_a = {"Authorization": f"Bearer {test_setup['token_a']}"}

            # 1. User B attempts to delete User A's media item
            res_tamper = await client.delete(f"/api/v1/media/{media_id}", headers=headers_b)
            assert res_tamper.status_code == 403
            assert res_tamper.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"

            # 2. Author User A deletes own media
            res_del = await client.delete(f"/api/v1/media/{media_id}", headers=headers_a)
            assert res_del.status_code == 200
            assert res_del.json()["message"] == "Media item deleted successfully."
            mock_storage_service.delete_object.assert_called_with(media.storage_key)

            # 3. Subsequent delete returns 404
            res_not_found = await client.delete(f"/api/v1/media/{media_id}", headers=headers_a)
            assert res_not_found.status_code == 404
            assert res_not_found.json()["error"]["code"] == "MEDIA_NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_storage_service, None)


@pytest.mark.asyncio
async def test_media_upload_spoofed_mime_and_size_enforcement(test_setup, mock_storage_service):
    """Verify that spoofed MIME, empty files, and oversized files are rejected and cleaned up."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {test_setup['token_a']}"}
            post_id = test_setup["post"].id

            # 1. Spoofed MIME: client uploaded an executable shell script disguised as a .jpg
            bad_key_spoofed = f"posts/{post_id}/{uuid.uuid4()}.jpg"
            mock_storage_service.get_object_metadata.return_value = {
                "content_length": 1024,
                "content_type": "image/jpeg",
            }
            fake_script = b"#!/bin/bash\necho 'malicious script'"
            mock_storage_service.get_object_header.side_effect = lambda *a, **k: fake_script
            mock_storage_service.delete_object.reset_mock()

            res_spoofed = await client.post(
                "/api/v1/media/complete",
                json={"post_id": str(post_id), "storage_key": bad_key_spoofed},
                headers=headers,
            )
            assert res_spoofed.status_code == 400
            assert res_spoofed.json()["error"]["code"] == "INVALID_FILE_SIGNATURE"
            mock_storage_service.delete_object.assert_called_with(bad_key_spoofed)

            # 2. Oversized file: actual file size in object store exceeds 10 MB limit
            bad_key_oversized = f"posts/{post_id}/{uuid.uuid4()}.jpg"
            mock_storage_service.get_object_metadata.return_value = {
                "content_length": 15 * 1024 * 1024,  # 15 MB
                "content_type": "image/jpeg",
            }
            jpeg_hdr = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
            mock_storage_service.get_object_header.side_effect = lambda *a, **k: jpeg_hdr
            mock_storage_service.delete_object.reset_mock()

            res_oversized = await client.post(
                "/api/v1/media/complete",
                json={"post_id": str(post_id), "storage_key": bad_key_oversized},
                headers=headers,
            )
            assert res_oversized.status_code == 400
            assert res_oversized.json()["error"]["code"] == "FILE_TOO_LARGE"
            mock_storage_service.delete_object.assert_called_with(bad_key_oversized)

            # 3. Empty file: 0 bytes uploaded
            bad_key_empty = f"posts/{post_id}/{uuid.uuid4()}.jpg"
            mock_storage_service.get_object_metadata.return_value = {
                "content_length": 0,
                "content_type": "image/jpeg",
            }
            mock_storage_service.delete_object.reset_mock()

            res_empty = await client.post(
                "/api/v1/media/complete",
                json={"post_id": str(post_id), "storage_key": bad_key_empty},
                headers=headers,
            )
            assert res_empty.status_code == 400
            assert res_empty.json()["error"]["code"] == "INVALID_FILE_SIZE"
            mock_storage_service.delete_object.assert_called_with(bad_key_empty)
    finally:
        app.dependency_overrides.pop(get_storage_service, None)
