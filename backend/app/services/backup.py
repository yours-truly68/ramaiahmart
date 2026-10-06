import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class BackupGeneration:
    """Represents a synchronized disaster recovery backup snapshot."""

    generation_id: str
    created_at: datetime
    user_ids: set[uuid.UUID]
    record_counts: dict[str, int]
    is_verified: bool = False
    is_promoted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "created_at": self.created_at.isoformat(),
            "user_count": len(self.user_ids),
            "record_counts": self.record_counts,
            "is_verified": self.is_verified,
            "is_promoted": self.is_promoted,
            "metadata": self.metadata,
        }


class BackupService:
    """Disaster recovery backup synchronization service.

    Implements a 7-day rolling disaster-recovery snapshot model where:
      1. New backups reflect current production database state.
      2. Permanently deleted accounts are omitted from new backup generations.
      3. Previous known-good backups remain intact until new backups are verified and promoted.
      4. Rolling retention preserves at most 7 generations.
    """

    def __init__(self, max_retention: int = 7) -> None:
        self.max_retention = max_retention
        self.generations: list[BackupGeneration] = []
        self.active_backup: BackupGeneration | None = None

    def create_generation(
        self, db: Session, simulate_failure: bool = False
    ) -> BackupGeneration:
        """Create a new backup snapshot generation from the current production state."""
        if simulate_failure:
            raise RuntimeError("Disaster recovery snapshot generation failed.")

        now = datetime.now(UTC)
        generation_id = f"backup_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Authoritative current production users
        current_users = db.scalars(select(User)).all()
        user_ids = {u.id for u in current_users}

        record_counts = {
            "users": len(user_ids),
        }

        generation = BackupGeneration(
            generation_id=generation_id,
            created_at=now,
            user_ids=user_ids,
            record_counts=record_counts,
            is_verified=False,
            is_promoted=False,
            metadata={
                "retention_policy_days": self.max_retention,
                "schema_version": "1.0",
            },
        )
        return generation

    def verify_generation(self, generation: BackupGeneration) -> bool:
        """Verify structural integrity and consistency of a new backup generation."""
        if not generation.generation_id or not generation.created_at:
            return False
        if generation.record_counts.get("users", -1) < 0:
            return False

        generation.is_verified = True
        return True

    def promote_generation(self, generation: BackupGeneration) -> None:
        """Promote a verified generation and prune generations beyond retention."""
        if not generation.is_verified:
            raise ValueError("Cannot promote unverified backup generation.")

        generation.is_promoted = True
        self.active_backup = generation
        self.generations.append(generation)

        # Enforce rolling retention: keep only the latest max_retention generations
        if len(self.generations) > self.max_retention:
            retired = self.generations[:-self.max_retention]
            self.generations = self.generations[-self.max_retention:]
            for r in retired:
                logger.info("Retired old backup generation: %s", r.generation_id)

    def synchronize(
        self, db: Session, simulate_failure: bool = False
    ) -> BackupGeneration:
        """Full disaster-recovery backup synchronization workflow:

        1. Create new backup generation from current production state.
        2. Verify new backup generation integrity.
        3. Promote new backup and retire previous backup generation.
        If any step fails, the previous active backup is strictly retained.
        """
        previous_backup = self.active_backup
        try:
            new_generation = self.create_generation(db, simulate_failure=simulate_failure)
            if not self.verify_generation(new_generation):
                raise RuntimeError("Backup generation verification failed.")

            self.promote_generation(new_generation)
            logger.info(
                "Successfully synchronized and promoted backup generation: %s",
                new_generation.generation_id,
            )
            return new_generation
        except Exception as e:
            logger.error(
                "Backup synchronization aborted: %s. Previous backup remains intact: %s",
                e,
                previous_backup.generation_id if previous_backup else "None",
            )
            # Guarantee previous known-good backup remains active
            self.active_backup = previous_backup
            raise

    def is_user_in_backup(
        self, generation: BackupGeneration, user_id: uuid.UUID
    ) -> bool:
        """Check if a user ID is represented in a specific backup generation."""
        return user_id in generation.user_ids


backup_service = BackupService()
