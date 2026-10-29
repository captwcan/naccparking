from __future__ import annotations

from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from streamlit.testing.v1 import AppTest
from services.google_sheets_service import connect_spreadsheet, load_google_sheets_settings


def main() -> int:
    app_path = Path(__file__).resolve().parents[1] / "app_parking.py"
    app = AppTest.from_file(str(app_path))
    if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
        settings = load_google_sheets_settings()
        book = connect_spreadsheet(settings)
        expected_id = os.getenv("EXPECTED_SPREADSHEET_ID")
        if expected_id and book.id != expected_id:
            raise RuntimeError("Smoke test credentials target an unexpected workbook")
        # Require the migrated tabs before running the UI; do not initialize anything.
        for name in ("RawData", "Settings", "ReportData"):
            book.worksheet(name)
        app.secrets["gcp_service_account"] = settings.service_account_info
        app.secrets["spreadsheet_url"] = settings.spreadsheet_url
    app.run(timeout=90)
    if app.exception:
        raise RuntimeError(f"Streamlit exceptions: {list(app.exception)}")
    if app.error:
        raise RuntimeError(f"Streamlit errors: {list(app.error)}")
    print("Streamlit recording page loaded with live workbook without errors; no records written")
    app.switch_page("pages/dashboard.py").run(timeout=90)
    if app.exception or app.error:
        raise RuntimeError("Live dashboard failed to load")
    print("Streamlit dashboard loaded with live workbook without errors; no records written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
