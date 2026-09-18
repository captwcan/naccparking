from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable
from zoneinfo import ZoneInfo

from services.archive_service import parse_parking_datetime
from services.monthly_ranking_service import (
    ARCHIVE_PATTERN,
    MonthStats,
    available_months,
    build_month_stats,
    source_sheet_for_month,
)


BANGKOK = ZoneInfo("Asia/Bangkok")
RAW_SHEET = "RawData"
CAR_SUMMARY_SHEET = "CarSummary"
MONTHLY_SHEET = "MonthlyRanking"
VISIBLE_SHEETS = (
    CAR_SUMMARY_SHEET,
    MONTHLY_SHEET,
    "DailyReport",
    "PrintReport",
    "DailySummary",
)
MONTHLY_ROWS = 1000
CAR_SUMMARY_ROWS = 8056
MONTH_OPTIONS_COLUMN = 16  # Q, zero based


@dataclass(frozen=True)
class VehicleStats:
    key: str
    plate: str
    province: str
    first_date: date
    last_date: date
    month_count: int
    day_count: int
    record_count: int
    buildings: frozenset[str]
    latest_buildings: frozenset[str]
    status: str


@dataclass(frozen=True)
class CombinedStats:
    source_rows: int
    invalid_dates: int
    vehicles: dict[str, VehicleStats]


@dataclass(frozen=True)
class WorkbookOrganizationPlan:
    current_month: date
    selected_month: date
    display_mode: str
    months: tuple[date, ...]
    source_names: tuple[str, ...]
    month_stats: dict[date, MonthStats]
    combined_stats: CombinedStats
    needs_update: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WorkbookOrganizationResult:
    backup_names: tuple[str, str]
    verified_months: tuple[date, ...]
    raw_data_unchanged: bool
    changed: bool


def build_combined_stats(
    values_by_sheet: dict[str, list[list[object]]],
) -> CombinedStats:
    records: dict[str, list[tuple[date, str, str, str]]] = {}
    source_rows = 0
    invalid_dates = 0

    for rows in values_by_sheet.values():
        for original in rows:
            row = list(original) + [""] * max(0, 6 - len(original))
            if not any(value not in (None, "") for value in row[:4]):
                continue
            source_rows += 1
            parsed = parse_parking_datetime(row[0])
            if parsed is None:
                invalid_dates += 1
                continue
            plate = str(row[2]).strip()
            province = str(row[3]).strip()
            key = str(row[5]).strip() or f"{plate}|{province}"
            if not key or key == "|":
                continue
            building = str(row[1]).strip()
            records.setdefault(key, []).append(
                (parsed.date(), building, plate, province)
            )

    vehicles: dict[str, VehicleStats] = {}
    for key, rows in records.items():
        days = {row[0] for row in rows}
        first_date = min(days)
        last_date = max(days)
        latest_rows = [row for row in rows if row[0] == last_date]
        streak = _latest_streak(days)
        vehicles[key] = VehicleStats(
            key=key,
            plate=next((row[2] for row in reversed(rows) if row[2]), ""),
            province=next((row[3] for row in reversed(rows) if row[3]), ""),
            first_date=first_date,
            last_date=last_date,
            month_count=len({(day.year, day.month) for day in days}),
            day_count=len(days),
            record_count=len(rows),
            buildings=frozenset(row[1] for row in rows if row[1]),
            latest_buildings=frozenset(row[1] for row in latest_rows if row[1]),
            status=_status_for_streak(streak),
        )
    return CombinedStats(source_rows, invalid_dates, vehicles)


def combined_summary_formula(source_names: Iterable[str]) -> str:
    sources = tuple(source_names)
    if not sources:
        raise ValueError("At least one source sheet is required")
    stack = "VSTACK(" + ",".join(_source_part(name) for name in sources) + ")"
    return (
        "=IFERROR(LET("
        f"source,{stack},"
        "sourceDates,ARRAYFORMULA(IFERROR(DATEVALUE(INDEX(source,,1)),INDEX(source,,1))),"
        "sourceBuildings,ARRAYFORMULA(TRIM(TO_TEXT(INDEX(source,,2)))),"
        "sourcePlates,INDEX(source,,3),sourceProvinces,INDEX(source,,4),"
        "sourceKeys,INDEX(source,,5),"
        "valid,FILTER({sourceDates,sourceBuildings,sourcePlates,sourceProvinces,sourceKeys},"
        'INDEX(source,,1)<>"",sourceKeys<>""),'
        "dates,INDEX(valid,,1),buildings,INDEX(valid,,2),plates,INDEX(valid,,3),"
        "provinces,INDEX(valid,,4),vehicleKeys,INDEX(valid,,5),"
        "keys,SORT(UNIQUE(vehicleKeys)),"
        "plateValues,MAP(keys,LAMBDA(k,INDEX(FILTER(plates,vehicleKeys=k),1))),"
        "provinceValues,MAP(keys,LAMBDA(k,INDEX(FILTER(provinces,vehicleKeys=k),1))),"
        "firstDates,MAP(keys,LAMBDA(k,MIN(FILTER(dates,vehicleKeys=k)))),"
        "lastDates,MAP(keys,LAMBDA(k,MAX(FILTER(dates,vehicleKeys=k)))),"
        "monthCounts,MAP(keys,LAMBDA(k,COUNTUNIQUE(ARRAYFORMULA(TEXT("
        'FILTER(dates,vehicleKeys=k),"yyyy-mm"))))),'
        "dayCounts,MAP(keys,LAMBDA(k,COUNTUNIQUE(FILTER(dates,vehicleKeys=k)))),"
        "recordCounts,MAP(keys,LAMBDA(k,ROWS(FILTER(vehicleKeys,vehicleKeys=k)))),"
        'allBuildings,MAP(keys,LAMBDA(k,IFERROR(TEXTJOIN(", ",TRUE,SORT(UNIQUE('
        'FILTER(buildings,vehicleKeys=k,buildings<>"")))) ,""))),'
        'latestBuildings,MAP(keys,lastDates,LAMBDA(k,lastd,IFERROR(TEXTJOIN(", ",TRUE,SORT(UNIQUE('
        'FILTER(buildings,vehicleKeys=k,dates=lastd,buildings<>"")))) ,""))),'
        "streaks,MAP(keys,LAMBDA(k,LET(ds,SORT(UNIQUE(FILTER(dates,vehicleKeys=k)),1,FALSE),"
        "last,INDEX(ds,1),seq,SEQUENCE(ROWS(ds),1,last,-1),"
        "IFERROR(MATCH(FALSE,ARRAYFORMULA(ISNUMBER(MATCH(seq,ds,0))),0)-1,ROWS(ds))))),"
        'statuses,ARRAYFORMULA(IF(streaks>=14,"แดงมาก",IF(streaks>=7,"เกิน 7 วัน",'
        'IF(streaks>=3,"เฝ้าดู","ปกติ")))),'
        "table,{keys,plateValues,provinceValues,firstDates,lastDates,monthCounts,"
        "dayCounts,recordCounts,allBuildings,latestBuildings,statuses},"
        'SORT(table,5,FALSE,2,TRUE)),"")'
    )


def monthly_summary_formula() -> str:
    return (
        "=IFERROR(LET(monthStart,DATE(YEAR($B$1),MONTH($B$1),1),"
        "monthEnd,EOMONTH(monthStart,0),"
        'sourceName,IF(monthStart=$Q$1,"RawData","Archive_"&TEXT(monthStart,"yyyy_mm")),'
        'sourceA,INDIRECT("\'"&sourceName&"\'!A2:A"),'
        'sourceB,INDIRECT("\'"&sourceName&"\'!B2:B"),'
        'sourceC,INDIRECT("\'"&sourceName&"\'!C2:C"),'
        'sourceD,INDIRECT("\'"&sourceName&"\'!D2:D"),'
        'sourceF,INDIRECT("\'"&sourceName&"\'!F2:F"),'
        "dates,ARRAYFORMULA(IFERROR(DATEVALUE(sourceA),sourceA)),"
        "valid,FILTER({dates,ARRAYFORMULA(TRIM(TO_TEXT(sourceB))),sourceC,sourceD,sourceF},"
        'dates>=monthStart,dates<=monthEnd,sourceA<>"",sourceF<>""),'
        "vDates,INDEX(valid,,1),vBuildings,INDEX(valid,,2),vPlates,INDEX(valid,,3),"
        "vProvinces,INDEX(valid,,4),vKeys,INDEX(valid,,5),"
        "firstDate,MIN(vDates),lastDate,MAX(vDates),periodDays,lastDate-firstDate+1,"
        "keys,SORT(UNIQUE(vKeys)),"
        "plateValues,MAP(keys,LAMBDA(k,INDEX(FILTER(vPlates,vKeys=k),1))),"
        "provinceValues,MAP(keys,LAMBDA(k,INDEX(FILTER(vProvinces,vKeys=k),1))),"
        "dayCounts,MAP(keys,LAMBDA(k,COUNTUNIQUE(FILTER(vDates,vKeys=k)))),"
        "firstDates,MAP(keys,LAMBDA(k,MIN(FILTER(vDates,vKeys=k)))),"
        "lastDates,MAP(keys,LAMBDA(k,MAX(FILTER(vDates,vKeys=k)))),"
        'allBuildings,MAP(keys,LAMBDA(k,IFERROR(TEXTJOIN(", ",TRUE,SORT(UNIQUE('
        'FILTER(vBuildings,vKeys=k,vBuildings<>"")))) ,""))),'
        'latestBuildings,MAP(keys,lastDates,LAMBDA(k,lastd,IFERROR(TEXTJOIN(", ",TRUE,SORT(UNIQUE('
        'FILTER(vBuildings,vKeys=k,vDates=lastd,vBuildings<>"")))) ,""))),'
        'statuses,ARRAYFORMULA(IF(lastDates=lastDate,"ยังเจอ","ไม่เจอ")),'
        "table,{keys,plateValues,provinceValues,dayCounts,ARRAYFORMULA(dayCounts/periodDays),"
        "firstDates,lastDates,allBuildings,latestBuildings,statuses},"
        "ranked,SORT(table,4,FALSE,2,TRUE),"
        'FILTER(ranked,IF($B$2="เฉพาะเกิน 80%",INDEX(ranked,,5)>0.8,'
        'INDEX(ranked,,1)<>""))),"")'
    )


def first_or_last_date_formula(function_name: str) -> str:
    if function_name not in {"MIN", "MAX"}:
        raise ValueError("function_name must be MIN or MAX")
    return (
        "=IFERROR(LET(monthStart,DATE(YEAR($B$1),MONTH($B$1),1),"
        'sourceName,IF(monthStart=$Q$1,"RawData","Archive_"&TEXT(monthStart,"yyyy_mm")),'
        'rawDates,INDIRECT("\'"&sourceName&"\'!A2:A"),'
        'dates,FILTER(ARRAYFORMULA(IFERROR(DATEVALUE(rawDates),rawDates)),rawDates<>""),'
        f'{function_name}(FILTER(dates,dates>=monthStart,dates<=EOMONTH(monthStart,0)))),"")'
    )


def build_summary_update_requests(
    car_sheet_id: int,
    monthly_sheet_id: int,
    *,
    current_month: date,
    selected_month: date,
    display_mode: str,
    months: tuple[date, ...],
    source_names: tuple[str, ...],
    metadata: dict[str, object],
) -> list[dict[str, object]]:
    requests: list[dict[str, object]] = []
    requests.extend(
        _delete_conditional_format_requests(metadata, {car_sheet_id, monthly_sheet_id})
    )
    requests.extend(
        [
            {"clearBasicFilter": {"sheetId": car_sheet_id}},
            {"clearBasicFilter": {"sheetId": monthly_sheet_id}},
            _clear_values_request(car_sheet_id, 0, CAR_SUMMARY_ROWS, 0, 11),
            _clear_values_request(monthly_sheet_id, 2, MONTHLY_ROWS, 0, 15),
            _row_values_request(
                car_sheet_id,
                0,
                0,
                [
                    "ทะเบียนรถ+จังหวัด",
                    "ทะเบียน",
                    "จังหวัด",
                    "พบครั้งแรก",
                    "พบล่าสุด",
                    "จำนวนเดือนที่พบ",
                    "จำนวนวันที่พบ",
                    "จำนวนรายการ",
                    "อาคารที่เคยพบ",
                    "อาคารล่าสุด",
                    "สถานะล่าสุด",
                ],
            ),
            _single_cell_request(
                car_sheet_id,
                1,
                0,
                formula=combined_summary_formula(source_names),
            ),
            _single_cell_request(monthly_sheet_id, 0, 0, text="เลือกเดือน"),
            _single_cell_request(
                monthly_sheet_id, 0, 1, number=_date_serial(selected_month)
            ),
            _single_cell_request(monthly_sheet_id, 0, 2, text="# เดือนนี้เริ่มบันทึก"),
            _single_cell_request(
                monthly_sheet_id,
                0,
                3,
                formula=first_or_last_date_formula("MIN"),
            ),
            _single_cell_request(monthly_sheet_id, 0, 4, text="ถึง"),
            _single_cell_request(
                monthly_sheet_id,
                0,
                5,
                formula=first_or_last_date_formula("MAX"),
            ),
            _single_cell_request(monthly_sheet_id, 0, 6, text="| นับ"),
            _single_cell_request(
                monthly_sheet_id,
                0,
                7,
                formula='=IF(OR(D1="",F1=""),"",F1-D1+1)',
            ),
            _single_cell_request(monthly_sheet_id, 0, 8, text="วัน"),
            _single_cell_request(monthly_sheet_id, 0, 9, text="| 80% ="),
            _single_cell_request(
                monthly_sheet_id,
                0,
                10,
                formula='=IF(H1="","",ROUNDUP(H1*80%,0))',
            ),
            _single_cell_request(monthly_sheet_id, 0, 11, text="วันขึ้นไป"),
            _single_cell_request(monthly_sheet_id, 1, 0, text="แสดง"),
            _single_cell_request(monthly_sheet_id, 1, 1, text=display_mode),
            _row_values_request(
                monthly_sheet_id,
                2,
                0,
                [
                    "ทะเบียนรถ+จังหวัด",
                    "ทะเบียน",
                    "จังหวัด",
                    "จำนวนวันที่พบ",
                    "% ของช่วง",
                    "วันที่แรกในเดือน",
                    "วันที่ล่าสุดในเดือน",
                    "อาคารที่พบ",
                    "อาคารล่าสุด",
                    "สถานะ",
                ],
            ),
            _single_cell_request(
                monthly_sheet_id, 3, 0, formula=monthly_summary_formula()
            ),
            _month_options_request(monthly_sheet_id, current_month, months),
            _month_validation_request(monthly_sheet_id),
            _display_mode_validation_request(monthly_sheet_id),
            _sheet_grid_request(car_sheet_id, frozen_rows=1),
            _sheet_grid_request(monthly_sheet_id, frozen_rows=3),
            _header_format_request(car_sheet_id, 0, 1, 0, 11),
            _header_format_request(monthly_sheet_id, 2, 3, 0, 10),
            _control_format_request(monthly_sheet_id, 0, 2, 0, 12),
            _date_format_request(car_sheet_id, 1, 3, CAR_SUMMARY_ROWS, 5),
            _date_format_request(monthly_sheet_id, 0, 1, 1, 2),
            _date_format_request(monthly_sheet_id, 0, 3, 1, 4),
            _date_format_request(monthly_sheet_id, 0, 5, 1, 6),
            _date_format_request(monthly_sheet_id, 3, 5, MONTHLY_ROWS, 7),
            _date_format_request(
                monthly_sheet_id,
                0,
                MONTH_OPTIONS_COLUMN,
                MONTHLY_ROWS,
                MONTH_OPTIONS_COLUMN + 1,
            ),
            _percent_format_request(monthly_sheet_id, 3, 4, MONTHLY_ROWS, 5),
            _hidden_column_request(car_sheet_id, 0, 1, True),
            _hidden_column_request(monthly_sheet_id, 0, 1, True),
            _hidden_column_request(
                monthly_sheet_id,
                MONTH_OPTIONS_COLUMN,
                MONTH_OPTIONS_COLUMN + 1,
                True,
            ),
            _set_basic_filter_request(car_sheet_id, 0, CAR_SUMMARY_ROWS, 0, 11),
            _set_basic_filter_request(monthly_sheet_id, 2, MONTHLY_ROWS, 0, 10),
        ]
    )
    requests.extend(_column_width_requests(car_sheet_id, is_monthly=False))
    requests.extend(_column_width_requests(monthly_sheet_id, is_monthly=True))
    requests.extend(
        _status_conditional_format_requests(car_sheet_id, 10, 1, CAR_SUMMARY_ROWS)
    )
    requests.append(_monthly_percent_conditional_format_request(monthly_sheet_id))
    return requests


def build_tab_organization_requests(
    worksheets: Iterable[object],
) -> list[dict[str, object]]:
    worksheets = list(worksheets)
    by_title = {worksheet.title: worksheet for worksheet in worksheets}
    missing = [title for title in VISIBLE_SHEETS if title not in by_title]
    if missing:
        raise RuntimeError(f"Missing visible sheet(s): {', '.join(missing)}")

    colors = (
        {"red": 0.18, "green": 0.45, "blue": 0.82},
        {"red": 0.10, "green": 0.60, "blue": 0.55},
        {"red": 0.22, "green": 0.68, "blue": 0.36},
        {"red": 0.55, "green": 0.35, "blue": 0.75},
        {"red": 0.45, "green": 0.50, "blue": 0.58},
    )
    requests: list[dict[str, object]] = []
    for index, (title, color) in enumerate(zip(VISIBLE_SHEETS, colors)):
        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": by_title[title].id,
                        "index": index,
                        "hidden": False,
                        "tabColorStyle": {"rgbColor": color},
                    },
                    "fields": "index,hidden,tabColorStyle",
                }
            }
        )

    hidden_index = len(VISIBLE_SHEETS)
    for worksheet in worksheets:
        if worksheet.title in VISIBLE_SHEETS:
            continue
        if not (
            worksheet.title == RAW_SHEET
            or ARCHIVE_PATTERN.fullmatch(worksheet.title)
            or worksheet.title.startswith("Backup_")
        ):
            continue
        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": worksheet.id,
                        "index": hidden_index,
                        "hidden": True,
                    },
                    "fields": "index,hidden",
                }
            }
        )
        hidden_index += 1
    return requests


def verify_monthly_values(values: list[list[object]], expected: MonthStats) -> None:
    if not expected.period_days:
        raise RuntimeError(f"No valid rows found in {expected.source_sheet}")
    actual_first = _serial_date(_cell(values, 0, 3))
    actual_last = _serial_date(_cell(values, 0, 5))
    if actual_first != expected.first_date or actual_last != expected.last_date:
        raise RuntimeError(
            f"Monthly dates mismatch for {expected.source_sheet}: "
            f"expected {expected.first_date}..{expected.last_date}, "
            f"got {actual_first}..{actual_last}"
        )
    if int(_cell(values, 0, 7)) != expected.period_days:
        raise RuntimeError(f"Monthly period mismatch for {expected.source_sheet}")

    actual: dict[str, tuple[int, float]] = {}
    for row in values[3:]:
        key = str(row[0]).strip() if row else ""
        if not key:
            continue
        count = int(row[3]) if len(row) > 3 and row[3] not in (None, "") else 0
        percent = float(row[4]) if len(row) > 4 and row[4] not in (None, "") else 0.0
        actual[key] = (count, percent)
    if set(actual) != set(expected.days_by_key):
        raise RuntimeError(
            f"Monthly vehicle mismatch for {expected.source_sheet}: "
            f"expected {len(expected.days_by_key)}, got {len(actual)}"
        )
    for key, days in expected.days_by_key.items():
        count, percent = actual[key]
        if count != len(days) or abs(percent - len(days) / expected.period_days) > 1e-9:
            raise RuntimeError(f"Monthly count mismatch for {key}")


def verify_combined_values(values: list[list[object]], expected: CombinedStats) -> None:
    actual = {
        str(row[0]).strip(): row for row in values[1:] if row and str(row[0]).strip()
    }
    if set(actual) != set(expected.vehicles):
        raise RuntimeError(
            f"Combined vehicle mismatch: expected {len(expected.vehicles)}, got {len(actual)}"
        )
    for key, stats in expected.vehicles.items():
        row = actual[key]
        first_date = _serial_date(row[3] if len(row) > 3 else "")
        last_date = _serial_date(row[4] if len(row) > 4 else "")
        counts = tuple(int(row[index]) for index in (5, 6, 7))
        status = str(row[10]).strip() if len(row) > 10 else ""
        if (first_date, last_date) != (stats.first_date, stats.last_date):
            raise RuntimeError(f"Combined date mismatch for {key}")
        expected_counts = (stats.month_count, stats.day_count, stats.record_count)
        if counts != expected_counts:
            raise RuntimeError(
                f"Combined count mismatch for {key}: "
                f"expected {expected_counts}, got {counts}"
            )
        if status != stats.status:
            raise RuntimeError(
                f"Combined status mismatch for {key}: "
                f"expected {stats.status!r}, got {status!r}"
            )
        latest = {
            value.strip()
            for value in str(row[9] if len(row) > 9 else "").split(",")
            if value.strip()
        }
        if latest != set(stats.latest_buildings):
            raise RuntimeError(f"Combined latest building mismatch for {key}")


class WorkbookOrganizer:
    def __init__(self, spreadsheet, logger):
        self.spreadsheet = spreadsheet
        self.logger = logger

    def load_plan(self, *, now: datetime | None = None) -> WorkbookOrganizationPlan:
        current = (now or datetime.now(BANGKOK)).astimezone(BANGKOK)
        current_month = date(current.year, current.month, 1)
        worksheets = self.spreadsheet.worksheets()
        titles = [worksheet.title for worksheet in worksheets]
        for required in (RAW_SHEET, CAR_SUMMARY_SHEET, MONTHLY_SHEET, *VISIBLE_SHEETS):
            if required not in titles:
                raise RuntimeError(f"Missing sheet: {required}")

        months = available_months(titles, current_month)
        source_names = tuple(
            source_sheet_for_month(month, current_month) for month in sorted(months)
        )
        response = self.spreadsheet.values_batch_get(
            [f"'{_escape(name)}'!A2:F" for name in source_names],
            params={
                "valueRenderOption": "FORMATTED_VALUE",
                "dateTimeRenderOption": "FORMATTED_STRING",
            },
        )
        ranges = response.get("valueRanges", [])
        values_by_sheet = {
            name: ranges[index].get("values", []) if index < len(ranges) else []
            for index, name in enumerate(source_names)
        }
        month_stats = {
            month: build_month_stats(
                month,
                source_sheet_for_month(month, current_month),
                values_by_sheet[source_sheet_for_month(month, current_month)],
            )
            for month in months
        }
        combined = build_combined_stats(values_by_sheet)

        controls = self.spreadsheet.values_batch_get(
            [
                f"'{MONTHLY_SHEET}'!B1",
                f"'{MONTHLY_SHEET}'!B2",
                f"'{CAR_SUMMARY_SHEET}'!A1:K2",
                f"'{MONTHLY_SHEET}'!A3:J4",
            ],
            params={
                "valueRenderOption": "FORMULA",
                "dateTimeRenderOption": "FORMATTED_STRING",
            },
        ).get("valueRanges", [])
        selected_value = _first_value(controls, 0)
        selected_parsed = parse_parking_datetime(selected_value)
        selected_month = (
            selected_parsed.date().replace(day=1)
            if selected_parsed and selected_parsed.date().replace(day=1) in months
            else current_month
        )
        display_mode = str(_first_value(controls, 1)).strip()
        if display_mode not in {"ทั้งหมด", "เฉพาะเกิน 80%"}:
            display_mode = "ทั้งหมด"

        reasons: list[str] = []
        car_values = controls[2].get("values", []) if len(controls) > 2 else []
        monthly_values = controls[3].get("values", []) if len(controls) > 3 else []
        if _cell(car_values, 1, 0) != combined_summary_formula(source_names):
            reasons.append("CarSummary is not the all-month summary")
        if _cell(monthly_values, 1, 0) != monthly_summary_formula():
            reasons.append("MonthlyRanking is not the compact monthly summary")

        metadata = self.spreadsheet.fetch_sheet_metadata(
            params={"fields": "sheets(properties(sheetId,title,index,hidden))"}
        )
        properties = {
            item["properties"]["title"]: item["properties"]
            for item in metadata.get("sheets", [])
        }
        for index, title in enumerate(VISIBLE_SHEETS):
            prop = properties.get(title, {})
            if prop.get("hidden") or prop.get("index") != index:
                reasons.append("visible tabs are not ordered")
                break
        for title, prop in properties.items():
            should_hide = (
                title == RAW_SHEET
                or ARCHIVE_PATTERN.fullmatch(title)
                or title.startswith("Backup_")
            )
            if should_hide and not prop.get("hidden", False):
                reasons.append("source or backup tabs are still visible")
                break

        return WorkbookOrganizationPlan(
            current_month=current_month,
            selected_month=selected_month,
            display_mode=display_mode,
            months=months,
            source_names=source_names,
            month_stats=month_stats,
            combined_stats=combined,
            needs_update=bool(reasons),
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def execute(
        self,
        plan: WorkbookOrganizationPlan,
        *,
        now: datetime | None = None,
    ) -> WorkbookOrganizationResult:
        if not plan.needs_update:
            return WorkbookOrganizationResult(("", ""), (), True, False)

        current = (now or datetime.now(BANGKOK)).astimezone(BANGKOK)
        car_sheet = self.spreadsheet.worksheet(CAR_SUMMARY_SHEET)
        monthly_sheet = self.spreadsheet.worksheet(MONTHLY_SHEET)
        raw_before = self._raw_data_fingerprint()
        timestamp = current.strftime("%Y%m%d_%H%M%S")
        car_backup_name = f"Backup_CarSummary_{timestamp}"
        monthly_backup_name = f"Backup_MonthlyRanking_{timestamp}"
        car_backup = self.spreadsheet.duplicate_sheet(
            car_sheet.id, new_sheet_name=car_backup_name
        )
        monthly_backup = self.spreadsheet.duplicate_sheet(
            monthly_sheet.id, new_sheet_name=monthly_backup_name
        )
        self.logger.info(
            "Backups created: %s, %s", car_backup_name, monthly_backup_name
        )

        try:
            metadata = self.spreadsheet.fetch_sheet_metadata(
                params={
                    "fields": (
                        "sheets(properties(sheetId,title,index,hidden),conditionalFormats)"
                    )
                }
            )
            requests = build_summary_update_requests(
                car_sheet.id,
                monthly_sheet.id,
                current_month=plan.current_month,
                selected_month=plan.selected_month,
                display_mode=plan.display_mode,
                months=plan.months,
                source_names=plan.source_names,
                metadata=metadata,
            )
            self.spreadsheet.batch_update({"requests": requests})
            self.spreadsheet.batch_update(
                {
                    "requests": build_tab_organization_requests(
                        self.spreadsheet.worksheets()
                    )
                }
            )

            self._wait_for_combined(plan.combined_stats)
            verify_months = _verification_months(plan)
            for month in verify_months:
                self._set_selected_month(monthly_sheet.id, month)
                self._set_display_mode(monthly_sheet.id, "ทั้งหมด")
                self._wait_for_month(plan.month_stats[month])
                self.logger.info("Verified monthly view: %s", month)
            self._set_selected_month(monthly_sheet.id, plan.selected_month)
            self._set_display_mode(monthly_sheet.id, plan.display_mode)

            raw_after = self._raw_data_fingerprint()
            if raw_after != raw_before:
                raise RuntimeError("RawData A:M changed during workbook organization")
        except Exception:
            self.logger.exception("Workbook organization failed; restoring summaries")
            self._restore(car_backup, car_sheet)
            self._restore(monthly_backup, monthly_sheet)
            raise

        return WorkbookOrganizationResult(
            (car_backup_name, monthly_backup_name),
            verify_months,
            True,
            True,
        )

    def _wait_for_combined(self, expected: CombinedStats) -> None:
        last_error: Exception | None = None
        for _ in range(60):
            values = self._read_values(f"'{CAR_SUMMARY_SHEET}'!A1:K{CAR_SUMMARY_ROWS}")
            try:
                verify_combined_values(values, expected)
                return
            except (RuntimeError, TypeError, ValueError) as exc:
                last_error = exc
                time.sleep(2)
        raise RuntimeError(f"CarSummary did not recalculate: {last_error}")

    def _wait_for_month(self, expected: MonthStats) -> None:
        last_error: Exception | None = None
        for _ in range(30):
            values = self._read_values(f"'{MONTHLY_SHEET}'!A1:J{MONTHLY_ROWS}")
            try:
                verify_monthly_values(values, expected)
                return
            except (RuntimeError, TypeError, ValueError) as exc:
                last_error = exc
                time.sleep(2)
        raise RuntimeError(f"MonthlyRanking did not recalculate: {last_error}")

    def _read_values(self, sheet_range: str) -> list[list[object]]:
        return (
            self.spreadsheet.values_batch_get(
                [sheet_range],
                params={
                    "valueRenderOption": "UNFORMATTED_VALUE",
                    "dateTimeRenderOption": "SERIAL_NUMBER",
                },
            )
            .get("valueRanges", [{}])[0]
            .get("values", [])
        )

    def _raw_data_fingerprint(self) -> str:
        values = (
            self.spreadsheet.values_batch_get(
                [f"'{RAW_SHEET}'!A1:M"],
                params={
                    "valueRenderOption": "FORMULA",
                    "dateTimeRenderOption": "FORMATTED_STRING",
                },
            )
            .get("valueRanges", [{}])[0]
            .get("values", [])
        )
        payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _set_selected_month(self, sheet_id: int, month: date) -> None:
        self.spreadsheet.batch_update(
            {
                "requests": [
                    _single_cell_request(sheet_id, 0, 1, number=_date_serial(month))
                ]
            }
        )

    def _set_display_mode(self, sheet_id: int, mode: str) -> None:
        self.spreadsheet.batch_update(
            {"requests": [_single_cell_request(sheet_id, 1, 1, text=mode)]}
        )

    def _restore(self, backup, destination) -> None:
        self.spreadsheet.batch_update(
            {
                "requests": [
                    {
                        "copyPaste": {
                            "source": {
                                "sheetId": backup.id,
                                "startRowIndex": 0,
                                "endRowIndex": destination.row_count,
                                "startColumnIndex": 0,
                                "endColumnIndex": destination.col_count,
                            },
                            "destination": {
                                "sheetId": destination.id,
                                "startRowIndex": 0,
                                "endRowIndex": destination.row_count,
                                "startColumnIndex": 0,
                                "endColumnIndex": destination.col_count,
                            },
                            "pasteType": "PASTE_NORMAL",
                            "pasteOrientation": "NORMAL",
                        }
                    }
                ]
            }
        )


def _verification_months(plan: WorkbookOrganizationPlan) -> tuple[date, ...]:
    result: list[date] = []
    archive_months = [month for month in plan.months if month != plan.current_month]
    if archive_months:
        result.append(archive_months[0])
    if plan.month_stats[plan.current_month].period_days:
        result.append(plan.current_month)
    if not result:
        raise RuntimeError("No source month has valid parking data")
    return tuple(result)


def _latest_streak(days: set[date]) -> int:
    ordered = sorted(days, reverse=True)
    if not ordered:
        return 0
    streak = 1
    for previous, current in zip(ordered, ordered[1:]):
        if (previous - current).days != 1:
            break
        streak += 1
    return streak


def _status_for_streak(streak: int) -> str:
    if streak >= 14:
        return "แดงมาก"
    if streak >= 7:
        return "เกิน 7 วัน"
    if streak >= 3:
        return "เฝ้าดู"
    return "ปกติ"


def _source_part(name: str) -> str:
    ref = f"'{_escape(name)}'"
    return (
        f"IFERROR(FILTER({{{ref}!A2:A,{ref}!B2:B,{ref}!C2:C,{ref}!D2:D,"
        f'{ref}!F2:F}},{ref}!A2:A<>""),{{"","","","",""}})'
    )


def _clear_values_request(
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
) -> dict[str, object]:
    return {
        "updateCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_column,
                "endColumnIndex": end_column,
            },
            "fields": "userEnteredValue",
        }
    }


def _row_values_request(
    sheet_id: int, row: int, column: int, values: list[str]
) -> dict[str, object]:
    return {
        "updateCells": {
            "start": {"sheetId": sheet_id, "rowIndex": row, "columnIndex": column},
            "rows": [
                {
                    "values": [
                        {"userEnteredValue": {"stringValue": value}} for value in values
                    ]
                }
            ],
            "fields": "userEnteredValue",
        }
    }


def _single_cell_request(
    sheet_id: int,
    row: int,
    column: int,
    *,
    formula: str | None = None,
    number: float | None = None,
    text: str | None = None,
) -> dict[str, object]:
    if formula is not None:
        value = {"formulaValue": formula}
    elif text is not None:
        value = {"stringValue": text}
    else:
        value = {"numberValue": number}
    return {
        "updateCells": {
            "start": {"sheetId": sheet_id, "rowIndex": row, "columnIndex": column},
            "rows": [{"values": [{"userEnteredValue": value}]}],
            "fields": "userEnteredValue",
        }
    }


def _month_options_request(
    sheet_id: int, current_month: date, months: tuple[date, ...]
) -> dict[str, object]:
    rows = [
        {"values": [{"userEnteredValue": {"numberValue": _date_serial(current_month)}}]}
    ]
    rows.extend(
        {"values": [{"userEnteredValue": {"numberValue": _date_serial(month)}}]}
        for month in months
    )
    rows.extend({"values": [{}]} for _ in range(MONTHLY_ROWS - len(rows)))
    return {
        "updateCells": {
            "start": {
                "sheetId": sheet_id,
                "rowIndex": 0,
                "columnIndex": MONTH_OPTIONS_COLUMN,
            },
            "rows": rows,
            "fields": "userEnteredValue",
        }
    }


def _month_validation_request(sheet_id: int) -> dict[str, object]:
    return {
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 1,
                "endColumnIndex": 2,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_RANGE",
                    "values": [{"userEnteredValue": "='MonthlyRanking'!$Q$2:$Q$1000"}],
                },
                "strict": True,
                "showCustomUi": True,
            },
        }
    }


def _display_mode_validation_request(sheet_id: int) -> dict[str, object]:
    return {
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": 2,
                "startColumnIndex": 1,
                "endColumnIndex": 2,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [
                        {"userEnteredValue": "ทั้งหมด"},
                        {"userEnteredValue": "เฉพาะเกิน 80%"},
                    ],
                },
                "strict": True,
                "showCustomUi": True,
            },
        }
    }


def _sheet_grid_request(sheet_id: int, *, frozen_rows: int) -> dict[str, object]:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": frozen_rows},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    }


def _header_format_request(
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
) -> dict[str, object]:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_column,
                "endColumnIndex": end_column,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.18, "green": 0.45, "blue": 0.82},
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "WRAP",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)",
        }
    }


def _control_format_request(
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
) -> dict[str, object]:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_column,
                "endColumnIndex": end_column,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.90, "green": 0.95, "blue": 1.0},
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,verticalAlignment)",
        }
    }


def _date_format_request(
    sheet_id: int,
    start_row: int,
    start_column: int,
    end_row: int,
    end_column: int,
) -> dict[str, object]:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_column,
                "endColumnIndex": end_column,
            },
            "cell": {
                "userEnteredFormat": {
                    "numberFormat": {"type": "DATE", "pattern": "d/m/yyyy"}
                }
            },
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def _percent_format_request(
    sheet_id: int,
    start_row: int,
    start_column: int,
    end_row: int,
    end_column: int,
) -> dict[str, object]:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_column,
                "endColumnIndex": end_column,
            },
            "cell": {
                "userEnteredFormat": {
                    "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
                }
            },
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def _hidden_column_request(
    sheet_id: int, start_column: int, end_column: int, hidden: bool
) -> dict[str, object]:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": start_column,
                "endIndex": end_column,
            },
            "properties": {"hiddenByUser": hidden},
            "fields": "hiddenByUser",
        }
    }


def _column_width_requests(
    sheet_id: int, *, is_monthly: bool
) -> list[dict[str, object]]:
    widths = (
        [170, 120, 120, 105, 105, 105, 105, 105, 240, 220, 110]
        if not is_monthly
        else [170, 120, 120, 105, 105, 115, 115, 240, 220, 100]
    )
    return [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": index,
                    "endIndex": index + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        }
        for index, width in enumerate(widths)
    ]


def _set_basic_filter_request(
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
) -> dict[str, object]:
    return {
        "setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_column,
                    "endColumnIndex": end_column,
                }
            }
        }
    }


def _status_conditional_format_requests(
    sheet_id: int, column: int, start_row: int, end_row: int
) -> list[dict[str, object]]:
    colors = {
        "ปกติ": {"red": 0.78, "green": 0.94, "blue": 0.82},
        "เฝ้าดู": {"red": 1.0, "green": 0.93, "blue": 0.62},
        "เกิน 7 วัน": {"red": 1.0, "green": 0.75, "blue": 0.45},
        "แดงมาก": {"red": 0.96, "green": 0.55, "blue": 0.55},
    }
    return [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": column,
                            "endColumnIndex": column + 1,
                        }
                    ],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": status}],
                        },
                        "format": {"backgroundColor": color},
                    },
                },
                "index": index,
            }
        }
        for index, (status, color) in enumerate(colors.items())
    ]


def _monthly_percent_conditional_format_request(sheet_id: int) -> dict[str, object]:
    return {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [
                    {
                        "sheetId": sheet_id,
                        "startRowIndex": 3,
                        "endRowIndex": MONTHLY_ROWS,
                        "startColumnIndex": 4,
                        "endColumnIndex": 5,
                    }
                ],
                "booleanRule": {
                    "condition": {
                        "type": "NUMBER_GREATER",
                        "values": [{"userEnteredValue": "0.8"}],
                    },
                    "format": {
                        "backgroundColor": {"red": 1.0, "green": 0.78, "blue": 0.45}
                    },
                },
            },
            "index": 0,
        }
    }


def _delete_conditional_format_requests(
    metadata: dict[str, object], sheet_ids: set[int]
) -> list[dict[str, object]]:
    requests: list[dict[str, object]] = []
    for item in metadata.get("sheets", []):
        sheet_id = item.get("properties", {}).get("sheetId")
        if sheet_id not in sheet_ids:
            continue
        count = len(item.get("conditionalFormats", []))
        requests.extend(
            {
                "deleteConditionalFormatRule": {
                    "sheetId": sheet_id,
                    "index": index,
                }
            }
            for index in range(count - 1, -1, -1)
        )
    return requests


def _cell(values: list[list[object]], row: int, column: int) -> object:
    if row >= len(values) or column >= len(values[row]):
        return ""
    return values[row][column]


def _first_value(value_ranges: list[dict[str, object]], index: int) -> object:
    if index >= len(value_ranges):
        return ""
    values = value_ranges[index].get("values", [])
    return values[0][0] if values and values[0] else ""


def _date_serial(value: date) -> float:
    return float((value - date(1899, 12, 30)).days)


def _serial_date(value: object) -> date | None:
    parsed = parse_parking_datetime(value)
    return parsed.date() if parsed else None


def _escape(name: str) -> str:
    return name.replace("'", "''")
