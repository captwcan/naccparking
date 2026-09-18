from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def main() -> int:
    app_path = Path(__file__).resolve().parents[1] / "app_parking.py"
    app = AppTest.from_file(str(app_path)).run(timeout=90)
    if app.exception:
        raise RuntimeError(f"Streamlit exceptions: {list(app.exception)}")
    if app.error:
        raise RuntimeError(f"Streamlit errors: {list(app.error)}")
    print("Streamlit website loaded and read RawData without errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
