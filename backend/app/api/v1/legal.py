from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.errors import AppException
from app.core.proxy import get_client_ip
from app.models.user import User
from app.schemas.legal import (
    LegalDocumentResponse,
    RecordConsentRequest,
    RecordConsentResponse,
    UserConsentStatusResponse,
)
from app.services.legal import (
    get_all_current_legal_documents,
    get_current_legal_document,
    get_user_consent_status,
    record_user_consent,
)

router = APIRouter(prefix="/legal", tags=["Legal"])


@router.get(
    "/documents",
    response_model=list[LegalDocumentResponse],
    summary="List active legal documents",
)
def list_legal_documents(
    db: Session = Depends(get_db),
) -> list[LegalDocumentResponse]:
    """Retrieve all currently active platform legal documents. Publicly accessible."""
    return get_all_current_legal_documents(db)


@router.get(
    "/documents/{document_type}",
    response_model=LegalDocumentResponse,
    summary="Get active legal document by type",
)
def get_legal_document(
    document_type: str,
    db: Session = Depends(get_db),
) -> LegalDocumentResponse:
    """Retrieve the current active legal document for 'TERMS' or 'PRIVACY'."""
    norm_type = document_type.upper().strip()
    if norm_type not in ("TERMS", "PRIVACY"):
        raise AppException(
            code="INVALID_DOCUMENT_TYPE",
            message="Document type must be 'TERMS' or 'PRIVACY'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    doc = get_current_legal_document(db, norm_type)
    if not doc:
        raise AppException(
            code="DOCUMENT_NOT_FOUND",
            message=f"No active document found for {norm_type}.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return doc


@router.get(
    "/consent-status",
    response_model=UserConsentStatusResponse,
    summary="Check authenticated user legal consent status",
)
def check_consent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserConsentStatusResponse:
    """Check whether the authenticated user has accepted the currently active legal documents."""
    return get_user_consent_status(db, current_user.id)


@router.post(
    "/consent",
    response_model=RecordConsentResponse,
    summary="Record consent to active legal document",
)
def record_consent(
    data: RecordConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordConsentResponse:
    """Record acceptance for the currently active version of a legal document (re-consent)."""
    norm_type = data.document_type.upper().strip()
    if norm_type not in ("TERMS", "PRIVACY"):
        raise AppException(
            code="INVALID_DOCUMENT_TYPE",
            message="Document type must be 'TERMS' or 'PRIVACY'.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    current_doc = get_current_legal_document(db, norm_type)
    if not current_doc:
        raise AppException(
            code="DOCUMENT_NOT_FOUND",
            message=f"No active document found for {norm_type}.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    consent = record_user_consent(
        db=db,
        user_id=current_user.id,
        document_type=norm_type,
        version=current_doc.version,
        ip_address=client_ip,
        user_agent=user_agent[:512] if user_agent else None,
    )
    db.commit()

    return RecordConsentResponse(
        message=f"Successfully recorded consent for {norm_type} version {current_doc.version}.",
        document_type=norm_type,
        version=current_doc.version,
        accepted_at=consent.accepted_at,
    )
