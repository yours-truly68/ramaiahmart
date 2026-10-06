import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_moderation_service
from app.core.config import settings
from app.core.errors import AppException
from app.db.session import get_db
from app.models.post import Post
from app.models.report import Report, ReportReason, ReportStatus
from app.models.user import User
from app.schemas.report import ReportCreateRequest, ReportResponse
from app.services.lifecycle import record_user_activity
from app.services.moderation import ModerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a marketplace listing",
)
def create_report(
    data: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    moderation_service: ModerationService = Depends(get_moderation_service),
) -> ReportResponse:
    """Submit a report against a marketplace listing.

    - Requires authentication.
    - Rate-limited to prevent abuse.
    - Prevents duplicate open reports for the same listing by the same user.
    - Authors cannot report their own listings.
    - Triggers reactive AI vision moderation ONLY for EXPLICIT_IMAGE and IMAGE_MISMATCH.
    - All other reasons (AUTHENTICITY_SUSPICION, SCAM, SPAM, OTHER) route to admin review.
    """
    # 1. Target Post Validation
    post = db.scalar(select(Post).options(selectinload(Post.images)).where(Post.id == data.post_id))
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="The listing you are attempting to report does not exist.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 2. Cannot report own post
    if post.author_id == current_user.id:
        raise AppException(
            code="CANNOT_REPORT_OWN_POST",
            message="You cannot submit a report against your own listing.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Duplicate Report Prevention
    active_report = db.scalar(
        select(Report).where(
            Report.post_id == post.id,
            Report.reporter_id == current_user.id,
            Report.status.in_(
                [ReportStatus.OPEN, ReportStatus.AI_REVIEWED, ReportStatus.UNDER_REVIEW]
            ),
        )
    )
    if active_report is not None:
        raise AppException(
            code="DUPLICATE_REPORT",
            message=(
                "You have already submitted a report for this listing. "
                "Our moderation team is reviewing it."
            ),
            status_code=status.HTTP_409_CONFLICT,
        )

    # 4. User-Level Rate Limiting
    window_start = datetime.now(UTC) - timedelta(seconds=settings.REPORTS_RATE_LIMIT_WINDOW_SECONDS)
    recent_reports_count = (
        db.scalar(
            select(func.count(Report.id)).where(
                Report.reporter_id == current_user.id,
                Report.created_at >= window_start,
            )
        )
        or 0
    )
    if recent_reports_count >= settings.REPORTS_RATE_LIMIT_PER_USER_WINDOW:
        raise AppException(
            code="RATE_LIMIT_EXCEEDED",
            message=(
                "You have submitted too many reports recently. "
                "Please wait before submitting additional reports."
            ),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # 5. Create Report Record
    report = Report(
        post_id=post.id,
        reporter_id=current_user.id,
        reason=data.reason,
        description=data.description.strip() if data.description else None,
        status=ReportStatus.OPEN,
        ai_reviewed=False,
    )
    db.add(report)
    db.flush()

    # 6. Reactive Vision Review Flow
    # Strictly trigger vision review ONLY for image-related reasons
    if data.reason in (ReportReason.EXPLICIT_IMAGE, ReportReason.IMAGE_MISMATCH):
        moderation_service.evaluate_report_image(report=report, post=post, db=db)
    else:
        # Non-image reasons remain for human admin review without invoking vision AI
        report.status = ReportStatus.OPEN
        report.ai_reviewed = False
        db.commit()

    record_user_activity(current_user, db, commit=True)
    db.refresh(report)

    logger.info(
        "Report created: report_id=%s post_id=%s reporter_id=%s reason=%s ai_reviewed=%s",
        report.id,
        post.id,
        current_user.id,
        report.reason.value,
        report.ai_reviewed,
    )

    return ReportResponse.model_validate(report)


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get report status",
)
def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Retrieve details and status of a submitted report. Reporter only."""
    report = db.scalar(select(Report).where(Report.id == report_id))
    if report is None:
        raise AppException(
            code="REPORT_NOT_FOUND",
            message="Report not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if report.reporter_id != current_user.id:
        raise AppException(
            code="FORBIDDEN_NOT_REPORTER",
            message="You do not have permission to view this report.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return ReportResponse.model_validate(report)
