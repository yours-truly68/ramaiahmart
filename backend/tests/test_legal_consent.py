import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.legal import LegalConsent, LegalDocument
from app.models.user import User


@pytest.mark.asyncio
async def test_registration_without_terms_fails():
    """Registration without explicit Terms consent is rejected."""
    email = f"noterms_{uuid.uuid4().hex[:6]}@msrit.edu"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "name": "Consent Test",
                "accepted_terms": False,
                "accepted_privacy": True,
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"]["code"] == "LEGAL_CONSENT_REQUIRED"


@pytest.mark.asyncio
async def test_registration_without_privacy_fails():
    """Registration without explicit Privacy consent is rejected."""
    email = f"nopriv_{uuid.uuid4().hex[:6]}@msrit.edu"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "name": "Consent Test",
                "accepted_terms": True,
                "accepted_privacy": False,
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"]["code"] == "LEGAL_CONSENT_REQUIRED"


@pytest.mark.asyncio
async def test_registration_with_consent_creates_audit_records():
    """Registration with consent records LegalConsent rows transactionally."""
    email = f"consent_ok_{uuid.uuid4().hex[:6]}@msrit.edu"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "name": "Consent Ok",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
            headers={"User-Agent": "TestBrowser/1.0", "X-Forwarded-For": "198.51.100.22"},
        )
        assert resp.status_code == 201

        db = SessionLocal()
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None

        consents = list(
            db.scalars(
                select(LegalConsent)
                .where(LegalConsent.user_id == user.id)
                .order_by(LegalConsent.document_type.asc())
            ).all()
        )
        assert len(consents) == 2

        privacy_consent = consents[0]
        assert privacy_consent.document_type == "PRIVACY"
        assert privacy_consent.document_version == "1.0"
        assert privacy_consent.user_agent == "TestBrowser/1.0"

        terms_consent = consents[1]
        assert terms_consent.document_type == "TERMS"
        assert terms_consent.document_version == "1.0"
        assert terms_consent.user_agent == "TestBrowser/1.0"

        db.close()


@pytest.mark.asyncio
async def test_public_legal_document_endpoints():
    """Public legal endpoints return active documents without authentication."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # List documents
        resp_list = await client.get("/api/v1/legal/documents")
        assert resp_list.status_code == 200
        docs = resp_list.json()
        assert len(docs) >= 2
        types = [d["document_type"] for d in docs]
        assert "TERMS" in types
        assert "PRIVACY" in types

        # Get TERMS
        resp_terms = await client.get("/api/v1/legal/documents/TERMS")
        assert resp_terms.status_code == 200
        assert resp_terms.json()["document_type"] == "TERMS"
        assert resp_terms.json()["is_current"] is True

        # Get PRIVACY (case-insensitive)
        resp_priv = await client.get("/api/v1/legal/documents/privacy")
        assert resp_priv.status_code == 200
        assert resp_priv.json()["document_type"] == "PRIVACY"

        # Invalid document type
        resp_inv = await client.get("/api/v1/legal/documents/UNKNOWN")
        assert resp_inv.status_code == 404
        assert resp_inv.json()["error"]["code"] == "INVALID_DOCUMENT_TYPE"


@pytest.mark.asyncio
async def test_user_consent_status_and_reconsent_flow():
    """Consent status detects version mismatches and allows re-consenting."""
    email = f"reconsent_{uuid.uuid4().hex[:6]}@msrit.edu"
    password = "Password123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Unauthenticated consent-status check fails
        unauth_resp = await client.get("/api/v1/legal/consent-status")
        assert unauth_resp.status_code == 401

        # 2. Register user with v1.0 consent
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "name": "Reconsent User",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        assert reg_resp.status_code == 201

        # 3. Log in to get access token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 4. Check initial consent status (both accepted at 1.0)
        status_resp = await client.get("/api/v1/legal/consent-status", headers=auth_headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["terms"]["accepted"] is True
        assert status_data["terms"]["current_version"] == "1.0"
        assert status_data["terms"]["accepted_version"] == "1.0"
        assert status_data["privacy"]["accepted"] is True
        assert status_data["privacy"]["current_version"] == "1.0"

        # 5. Simulate publication of Terms 1.1 in database
        db = SessionLocal()
        old_terms = db.scalar(
            select(LegalDocument).where(
                LegalDocument.document_type == "TERMS",
                LegalDocument.is_current.is_(True),
            )
        )
        if old_terms:
            old_terms.is_current = False

        new_terms = LegalDocument(
            document_type="TERMS",
            version="1.1",
            title="RamaiahMart Terms & Conditions v1.1",
            content="Updated terms for new campus safety requirements.",
            is_current=True,
            effective_at=datetime.now(UTC),
            published_at=datetime.now(UTC),
        )
        db.add(new_terms)
        db.commit()
        db.close()

        try:
            # 6. Consent status now shows Terms need re-consent!
            status_resp_2 = await client.get("/api/v1/legal/consent-status", headers=auth_headers)
            assert status_resp_2.status_code == 200
            data_2 = status_resp_2.json()
            assert data_2["terms"]["current_version"] == "1.1"
            assert data_2["terms"]["accepted_version"] == "1.0"
            assert data_2["terms"]["accepted"] is False  # Needs re-consent!
            assert data_2["privacy"]["accepted"] is True  # Privacy unchanged

            # 7. Perform re-consent via POST /api/v1/legal/consent
            reconsent_resp = await client.post(
                "/api/v1/legal/consent",
                json={"document_type": "TERMS"},
                headers=auth_headers,
            )
            assert reconsent_resp.status_code == 200
            assert reconsent_resp.json()["version"] == "1.1"

            # 8. Check consent status again (now both accepted)
            status_resp_3 = await client.get("/api/v1/legal/consent-status", headers=auth_headers)
            assert status_resp_3.status_code == 200
            data_3 = status_resp_3.json()
            assert data_3["terms"]["current_version"] == "1.1"
            assert data_3["terms"]["accepted_version"] == "1.1"
            assert data_3["terms"]["accepted"] is True
        finally:
            # Clean up database: set 1.0 back to is_current
            db = SessionLocal()
            t11 = db.scalar(select(LegalDocument).where(LegalDocument.version == "1.1"))
            if t11:
                db.delete(t11)
            t10 = db.scalar(select(LegalDocument).where(LegalDocument.version == "1.0"))
            if t10:
                t10.is_current = True
            db.commit()
            db.close()
