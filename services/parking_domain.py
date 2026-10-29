"""Shared identity and business clock for parking records."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

BANGKOK = ZoneInfo("Asia/Bangkok")

def bangkok_now():
    return datetime.now(BANGKOK)

def normalize_plate(value):
    return re.sub(r"[\s\-.‐‑‒–—]+", "", str(value or "").strip().upper())

def vehicle_key(plate, province):
    return normalize_plate(plate) + "|" + str(province or "").strip()
