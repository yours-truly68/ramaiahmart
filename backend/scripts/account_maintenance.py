"""Account maintenance job: inactivity sweep and permanent deletion.

Intended for periodic invocation by a production scheduler (cron, systemd timer,
or container-based scheduler). RamaiahMart deliberately does not introduce
Celery/Redis/Kubernetes for this in V1.

This operation is idempotent and safe to re-run:

  1. Inactivity sweep: ACTIVE accounts with no meaningful activity for 90 days
     transition to INACTIVE. Inactivity is non-destructive: nothing is deleted,
     nothing is suspended, and any meaningful activity reactivates the account.

  2. Permanent deletion: DELETION_PENDING accounts past their
     deletion_scheduled_at deadline are irreversibly deleted along with their
     posts, images, conversations, messages, tokens, consents, and object
     storage media. Missing storage objects do not abort the run.

Usage:
  python -m scripts.account_maintenance [--dry-run]

Example crontab entry (daily at 03:15):
  15 3 * * * cd /srv/ramaiahmart/backend && uv run python -m scripts.account_maintenance
"""

import argparse
import logging
import sys

from app.db.session import SessionLocal
from app.services.lifecycle import mark_inactive_accounts, process_permanent_deletions

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ramaiahmart.account_maintenance")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing (inactivity sweep only).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.dry_run:
            from datetime import UTC, datetime, timedelta

            from sqlalchemy import and_, or_, select

            from app.models.user import User, UserStatus

            cutoff = datetime.now(UTC) - timedelta(days=90)
            would_mark = db.scalars(
                select(User.id).where(
                    User.status == UserStatus.ACTIVE,
                    or_(
                        User.last_activity_at < cutoff,
                        and_(User.last_activity_at.is_(None), User.created_at < cutoff),
                    ),
                )
            ).all()
            logger.info("Dry run: %d accounts would be marked INACTIVE", len(would_mark))
            logger.info(
                "Dry run: %d deletions would execute",
                len(
                    db.scalars(
                        select(User.id).where(
                            User.status == UserStatus.DELETION_PENDING,
                            User.deletion_scheduled_at.is_not(None),
                            User.deletion_scheduled_at <= datetime.now(UTC),
                        )
                    ).all()
                ),
            )
            return 0

        marked = mark_inactive_accounts(db)
        logger.info("Inactivity sweep complete: %d accounts marked INACTIVE", len(marked))

        deleted = process_permanent_deletions(db)
        logger.info("Permanent deletion pass complete: %d accounts purged", len(deleted))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
