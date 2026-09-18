from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.google_sheets_service import connect_spreadsheet
from services.workbook_organization_service import WorkbookOrganizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create compact all-month and monthly parking views"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--yes", action="store_true")
    return parser.parse_args()


def confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logger = logging.getLogger("workbook-organizer")
    try:
        organizer = WorkbookOrganizer(connect_spreadsheet(), logger)
        plan = organizer.load_plan()
        logger.info("Months: %s", ", ".join(map(str, plan.months)))
        logger.info("Source rows: %s", f"{plan.combined_stats.source_rows:,}")
        logger.info("Unique vehicles: %s", f"{len(plan.combined_stats.vehicles):,}")
        logger.info("Invalid dates: %s", plan.combined_stats.invalid_dates)
        logger.info("Update required: %s", "yes" if plan.needs_update else "no")
        for reason in plan.reasons:
            logger.info("Reason: %s", reason)

        if args.dry_run:
            logger.info("Dry run completed. No data was modified.")
            return 0
        if not plan.needs_update:
            logger.info("Workbook is already organized. No data was modified.")
            return 0
        if not args.yes and not confirm("Back up and organize the workbook?"):
            logger.info("Workbook organization cancelled")
            return 0

        result = organizer.execute(plan)
        logger.info("Backups: %s", ", ".join(result.backup_names))
        logger.info("Verified months: %s", ", ".join(map(str, result.verified_months)))
        logger.info("RawData A:M unchanged: %s", result.raw_data_unchanged)
        logger.info("Workbook organized successfully")
        return 0
    except Exception:
        logger.exception("Workbook organization failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
