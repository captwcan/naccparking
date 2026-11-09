"""Shared identity and business clock for parking records."""
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

BANGKOK = ZoneInfo("Asia/Bangkok")
SUPPORTED_DATE_FORMATS = ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S")


def parse_parking_datetime(value):
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, date):
            parsed = datetime.combine(value, datetime.min.time())
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            parsed = datetime(1899, 12, 30) + timedelta(days=float(value))
        else:
            text = str(value).strip() if value is not None else ""
            if not text:
                return None
            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                parsed = None
                for fmt in SUPPORTED_DATE_FORMATS:
                    try:
                        parsed = datetime.strptime(text, fmt)
                        break
                    except ValueError:
                        continue
                if parsed is None:
                    return None
        return parsed.replace(tzinfo=BANGKOK) if parsed.tzinfo is None else parsed.astimezone(BANGKOK)
    except (ValueError, OverflowError, TypeError):
        return None


def parking_date_series(series):
    """Parse each supported cell independently into local Bangkok timestamps."""
    import pandas as pd
    parsed = pd.to_datetime(series.map(parse_parking_datetime), errors="coerce", utc=True)
    return parsed.dt.tz_convert(BANGKOK).dt.tz_localize(None)

def bangkok_now():
    return datetime.now(BANGKOK)

def normalize_plate(value):
    return re.sub(r"[\s\-.‐‑‒–—]+", "", str(value or "").strip().upper())

def vehicle_key(plate, province):
    return normalize_plate(plate) + "|" + str(province or "").strip()
