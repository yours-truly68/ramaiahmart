import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.moderation import ModerationDecision, ModerationResult
from app.models.post import Post, PostStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModerationInput:
    """Input payload submitted to a moderation provider."""

    title: str
    description: str
    category_slug: str | None = None
    category_name: str | None = None
    post_type: str = "OFFER"
    image_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModerationEvaluation:
    """Standardized result returned by a moderation provider."""

    decision: ModerationDecision
    risk_score: float
    reason_codes: list[str]
    provider: str
    model: str


class ModerationProvider(Protocol):
    """Pluggable provider interface for evaluating marketplace posts."""

    def evaluate_post(self, input_data: ModerationInput) -> ModerationEvaluation:
        """Evaluate post content and return a structured decision."""
        ...


class MockModerationProvider:
    """Deterministic mock moderation provider for testing and development.

    Detects prohibited goods/services, scams, abusive content, sexual content,
    spam, and misleading/unrelated images based on deterministic rules.
    """

    def __init__(self, name: str = "mock_provider", model: str = "mock_rule_engine_v1") -> None:
        self.name = name
        self.model = model

    def evaluate_post(self, input_data: ModerationInput) -> ModerationEvaluation:
        text = f"{input_data.title} {input_data.description}".lower()

        # Simulated provider crash for failure testing
        if "provider_crash" in text or "raise_error" in text:
            raise RuntimeError("Simulated moderation provider network failure")

        # 1. Prohibited Goods
        prohibited_goods = [
            "drug",
            "weed",
            "weapon",
            "gun",
            "counterfeit",
            "alcohol",
            "cigarette",
            "prescription",
        ]
        if any(kw in text for kw in prohibited_goods):
            return ModerationEvaluation(
                decision=ModerationDecision.REJECT,
                risk_score=0.98,
                reason_codes=["PROHIBITED_GOODS"],
                provider=self.name,
                model=self.model,
            )

        # 2. Prohibited Services
        prohibited_services = ["exam leak", "cheat code service", "proxy test", "hack"]
        if any(kw in text for kw in prohibited_services):
            return ModerationEvaluation(
                decision=ModerationDecision.REJECT,
                risk_score=0.95,
                reason_codes=["PROHIBITED_SERVICES"],
                provider=self.name,
                model=self.model,
            )

        # 3. Scams & Fraud
        scams = ["telegram", "wire transfer", "crypto transfer", "whatsapp only", "western union"]
        if any(kw in text for kw in scams):
            return ModerationEvaluation(
                decision=ModerationDecision.REJECT,
                risk_score=0.92,
                reason_codes=["SCAM_FRAUD"],
                provider=self.name,
                model=self.model,
            )

        # 4. Sexual Content
        sexual_content = ["nsfw", "porn", "adult service", "sexual"]
        if any(kw in text for kw in sexual_content):
            return ModerationEvaluation(
                decision=ModerationDecision.REJECT,
                risk_score=0.95,
                reason_codes=["SEXUAL_CONTENT"],
                provider=self.name,
                model=self.model,
            )

        # 5. Abusive Content
        abusive = ["hate speech", "harass", "abusive slur"]
        if any(kw in text for kw in abusive):
            return ModerationEvaluation(
                decision=ModerationDecision.REJECT,
                risk_score=0.90,
                reason_codes=["ABUSIVE_CONTENT"],
                provider=self.name,
                model=self.model,
            )

        # 6. Spam
        spam_indicators = ["free money now", "click here fast", "earn 5000 daily with zero work"]
        if any(kw in text for kw in spam_indicators):
            return ModerationEvaluation(
                decision=ModerationDecision.REJECT,
                risk_score=0.88,
                reason_codes=["SPAM"],
                provider=self.name,
                model=self.model,
            )

        # 7. Unrelated / Misleading Images
        if any("meme" in img.lower() or "spam" in img.lower() for img in input_data.image_keys):
            return ModerationEvaluation(
                decision=ModerationDecision.REJECT,
                risk_score=0.85,
                reason_codes=["UNRELATED_IMAGE"],
                provider=self.name,
                model=self.model,
            )

        # 8. Ambiguous content requiring manual review
        review_triggers = ["needs_review", "suspicious", "flagged", "expensive luxury watch"]
        if any(kw in text for kw in review_triggers):
            return ModerationEvaluation(
                decision=ModerationDecision.REVIEW,
                risk_score=0.60,
                reason_codes=["MANUAL_REVIEW_REQUIRED"],
                provider=self.name,
                model=self.model,
            )

        # 9. Clean listing approved
        return ModerationEvaluation(
            decision=ModerationDecision.APPROVE,
            risk_score=0.02,
            reason_codes=["SAFE_LISTING"],
            provider=self.name,
            model=self.model,
        )


class ModerationService:
    """Service boundary for content review and automated/manual moderation.

    Coordinates the active ModerationProvider, fails closed on provider error,
    applies the resulting status to the post, and writes the structured ModerationResult.
    """

    def __init__(self, provider: ModerationProvider | None = None) -> None:
        self.provider: ModerationProvider = provider or MockModerationProvider()

    def process_post_publication(self, post: Post, db: Session) -> Post:
        """Evaluate a post for publication and persist the moderation outcome.

        Fails closed: If provider throws or fails, post moves to PENDING_REVIEW (not PUBLISHED).
        """
        category_name = post.category.name if post.category else None
        category_slug = post.category.slug if post.category else None
        image_keys = [img.storage_key for img in post.images] if post.images else []

        input_data = ModerationInput(
            title=post.title,
            description=post.description,
            category_slug=category_slug,
            category_name=category_name,
            post_type=post.type.value if hasattr(post.type, "value") else str(post.type),
            image_keys=image_keys,
        )

        try:
            evaluation = self.provider.evaluate_post(input_data)
        except Exception as exc:
            logger.error("Moderation provider failure for post %s: %s", post.id, exc)
            # Safe fallback: fail closed to human review
            evaluation = ModerationEvaluation(
                decision=ModerationDecision.REVIEW,
                risk_score=1.0,
                reason_codes=["PROVIDER_FAILURE_FALLBACK"],
                provider="system_fallback",
                model="fail_closed_v1",
            )

        # Apply state transition based on decision
        if evaluation.decision == ModerationDecision.APPROVE:
            post.status = PostStatus.PUBLISHED
            post.published_at = datetime.now(UTC)
        elif evaluation.decision == ModerationDecision.REVIEW:
            post.status = PostStatus.PENDING_REVIEW
        elif evaluation.decision == ModerationDecision.REJECT:
            post.status = PostStatus.REJECTED

        # Record structured moderation evaluation
        mod_result = ModerationResult(
            post_id=post.id,
            decision=evaluation.decision,
            risk_score=evaluation.risk_score,
            reason_codes=evaluation.reason_codes,
            provider=evaluation.provider,
            model=evaluation.model,
        )
        db.add(mod_result)
        db.commit()
        db.refresh(post)

        return post

    def submit_for_review(self, post: Post, db: Session) -> Post:
        """Backwards-compatible alias for post publication processing."""
        return self.process_post_publication(post, db)


moderation_service = ModerationService()
