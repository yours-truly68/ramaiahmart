from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.moderation import ModerationDecision, ModerationResult
from app.models.post import Post, PostStatus


class ModerationService:
    """Service boundary for content review and automated/manual moderation."""

    def submit_for_review(self, post: Post, db: Session) -> Post:
        """Move post to PENDING_REVIEW status for moderation evaluation."""
        post.status = PostStatus.PENDING_REVIEW
        db.commit()
        db.refresh(post)
        return post

    def approve_post(
        self,
        post: Post,
        db: Session,
        provider: str = "system",
        model: str = "rule_engine_v1",
    ) -> Post:
        """Approve a post, setting it to PUBLISHED state with moderation record."""
        post.status = PostStatus.PUBLISHED
        post.published_at = datetime.now(UTC)

        mod_record = ModerationResult(
            post_id=post.id,
            decision=ModerationDecision.APPROVE,
            risk_score=0.0,
            reason_codes=["AUTOMATIC_APPROVAL"],
            provider=provider,
            model=model,
        )
        db.add(mod_record)
        db.commit()
        db.refresh(post)
        return post

    def reject_post(
        self,
        post: Post,
        db: Session,
        reason_codes: list[str],
        risk_score: float = 1.0,
        provider: str = "system",
        model: str = "rule_engine_v1",
    ) -> Post:
        """Reject a post with reason codes."""
        post.status = PostStatus.REJECTED

        mod_record = ModerationResult(
            post_id=post.id,
            decision=ModerationDecision.REJECT,
            risk_score=risk_score,
            reason_codes=reason_codes,
            provider=provider,
            model=model,
        )
        db.add(mod_record)
        db.commit()
        db.refresh(post)
        return post


moderation_service = ModerationService()
