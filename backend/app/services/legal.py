import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.legal import LegalConsent, LegalDocument
from app.schemas.legal import ConsentItemStatus, UserConsentStatusResponse


def ensure_default_legal_documents(db: Session) -> None:
    """Ensure baseline TERMS and PRIVACY 1.0 documents exist in the database."""
    types = ["TERMS", "PRIVACY"]
    for doc_type in types:
        existing = db.scalar(
            select(LegalDocument).where(
                LegalDocument.document_type == doc_type,
                LegalDocument.version == "1.0",
            )
        )
        if not existing:
            doc = LegalDocument(
                document_type=doc_type,
                version="1.0",
                title=(
                    "RamaiahMart Terms & Conditions"
                    if doc_type == "TERMS"
                    else "RamaiahMart Privacy Policy"
                ),
                content=(
                    "RamaiahMart Terms & Conditions governing student exchange on campus."
                    if doc_type == "TERMS"
                    else "RamaiahMart Privacy Policy explaining data handling on campus."
                ),
                is_current=True,
            )
            db.add(doc)
        else:
            has_current = db.scalar(
                select(LegalDocument).where(
                    LegalDocument.document_type == doc_type,
                    LegalDocument.is_current.is_(True),
                )
            )
            if not has_current:
                existing.is_current = True
    db.commit()


def get_current_legal_document(db: Session, document_type: str) -> LegalDocument:
    """Retrieve the currently active document for the requested category."""
    norm_type = document_type.upper().strip()
    doc = db.scalar(
        select(LegalDocument)
        .where(
            LegalDocument.document_type == norm_type,
            LegalDocument.is_current.is_(True),
        )
        .order_by(LegalDocument.effective_at.desc())
    )
    if not doc:
        ensure_default_legal_documents(db)
        doc = db.scalar(
            select(LegalDocument)
            .where(
                LegalDocument.document_type == norm_type,
                LegalDocument.is_current.is_(True),
            )
            .order_by(LegalDocument.effective_at.desc())
        )
    return doc


def get_all_current_legal_documents(db: Session) -> list[LegalDocument]:
    """Retrieve all current active legal documents."""
    docs = list(
        db.scalars(
            select(LegalDocument)
            .where(LegalDocument.is_current.is_(True))
            .order_by(LegalDocument.document_type.asc())
        ).all()
    )
    if len(docs) < 2:
        ensure_default_legal_documents(db)
        docs = list(
            db.scalars(
                select(LegalDocument)
                .where(LegalDocument.is_current.is_(True))
                .order_by(LegalDocument.document_type.asc())
            ).all()
        )
    return docs


def record_user_consent(
    db: Session,
    user_id: uuid.UUID,
    document_type: str,
    version: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> LegalConsent:
    """Record or update user acceptance of a specific legal document version."""
    norm_type = document_type.upper().strip()
    existing = db.scalar(
        select(LegalConsent).where(
            LegalConsent.user_id == user_id,
            LegalConsent.document_type == norm_type,
            LegalConsent.document_version == version,
        )
    )
    now = datetime.now(UTC)
    if existing:
        existing.accepted_at = now
        if ip_address:
            existing.ip_address = ip_address
        if user_agent:
            existing.user_agent = user_agent
        return existing

    consent = LegalConsent(
        user_id=user_id,
        document_type=norm_type,
        document_version=version,
        accepted_at=now,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(consent)
    return consent


def get_user_consent_status(db: Session, user_id: uuid.UUID) -> UserConsentStatusResponse:
    """Compare user acceptance records against currently active versions."""
    terms_doc = get_current_legal_document(db, "TERMS")
    privacy_doc = get_current_legal_document(db, "PRIVACY")

    terms_current_version = terms_doc.version if terms_doc else "1.0"
    privacy_current_version = privacy_doc.version if privacy_doc else "1.0"

    # Query latest consents for this user
    user_consents = list(
        db.scalars(
            select(LegalConsent)
            .where(LegalConsent.user_id == user_id)
            .order_by(LegalConsent.accepted_at.desc())
        ).all()
    )

    terms_consent = next((c for c in user_consents if c.document_type == "TERMS"), None)
    privacy_consent = next((c for c in user_consents if c.document_type == "PRIVACY"), None)

    terms_accepted = bool(
        terms_consent and terms_consent.document_version == terms_current_version
    )
    privacy_accepted = bool(
        privacy_consent and privacy_consent.document_version == privacy_current_version
    )

    return UserConsentStatusResponse(
        terms=ConsentItemStatus(
            current_version=terms_current_version,
            accepted_version=terms_consent.document_version if terms_consent else None,
            accepted=terms_accepted,
            accepted_at=terms_consent.accepted_at if terms_consent else None,
        ),
        privacy=ConsentItemStatus(
            current_version=privacy_current_version,
            accepted_version=privacy_consent.document_version if privacy_consent else None,
            accepted=privacy_accepted,
            accepted_at=privacy_consent.accepted_at if privacy_consent else None,
        ),
    )
