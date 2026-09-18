from __future__ import annotations

import unittest

from services.workbook_organization_service import (
    _formulas_equivalent,
    VISIBLE_SHEETS,
    build_combined_stats,
    build_tab_organization_requests,
    combined_summary_formula,
    monthly_summary_formula,
    verify_combined_values,
)


class Worksheet:
    def __init__(self, title: str, sheet_id: int):
        self.title = title
        self.id = sheet_id


class WorkbookOrganizationTests(unittest.TestCase):
    def test_combined_stats_uses_plate_and_province_key(self):
        values = {
            "Archive_2026_06": [
                [
                    "2026-06-30",
                    " อาคาร 4 ",
                    "กก1",
                    "กรุงเทพมหานคร",
                    "",
                    "กก1|กรุงเทพมหานคร",
                ],
            ],
            "RawData": [
                [
                    "2026-09-14",
                    "อาคาร 7",
                    "กก1",
                    "กรุงเทพมหานคร",
                    "",
                    "กก1|กรุงเทพมหานคร",
                ],
                [
                    "2026-09-15",
                    "อาคาร 8",
                    "กก1",
                    "กรุงเทพมหานคร",
                    "",
                    "กก1|กรุงเทพมหานคร",
                ],
                [
                    "2026-09-15",
                    "อาคาร 4",
                    "กก1",
                    "กรุงเทพมหานคร",
                    "",
                    "กก1|กรุงเทพมหานคร",
                ],
            ],
        }
        stats = build_combined_stats(values)
        vehicle = stats.vehicles["กก1|กรุงเทพมหานคร"]
        self.assertEqual(stats.source_rows, 4)
        self.assertEqual(vehicle.month_count, 2)
        self.assertEqual(vehicle.day_count, 3)
        self.assertEqual(vehicle.record_count, 4)
        self.assertEqual(vehicle.buildings, {"อาคาร 4", "อาคาร 7", "อาคาร 8"})
        self.assertEqual(vehicle.latest_buildings, {"อาคาร 4", "อาคาร 8"})
        self.assertEqual(vehicle.status, "ปกติ")

    def test_combined_formula_lists_only_requested_sources(self):
        formula = combined_summary_formula(("Archive_2026_06", "RawData"))
        self.assertIn("'Archive_2026_06'!A2:A", formula)
        self.assertIn("'RawData'!A2:A", formula)
        self.assertNotIn("Backup_", formula)
        self.assertIn("VSTACK", formula)
        self.assertIn("TRIM", formula)

    def test_formula_comparison_accepts_google_expanded_ranges(self):
        expected = "=VSTACK(FILTER('RawData'!A2:A,'RawData'!A2:A<>\"\"))"
        actual = '=VSTACK(FILTER(RawData!A2:A8056,RawData!A2:A8056<>""))'
        self.assertTrue(_formulas_equivalent(actual, expected))

    def test_monthly_formula_is_compact_and_keeps_filter(self):
        formula = monthly_summary_formula()
        self.assertIn('"เฉพาะเกิน 80%"', formula)
        self.assertIn("allBuildings", formula)
        self.assertIn("latestBuildings", formula)
        self.assertNotIn("buildingDays", formula)

    def test_tab_requests_keep_five_visible_and_hide_sources(self):
        sheets = [
            *(
                Worksheet(title, index + 1)
                for index, title in enumerate(VISIBLE_SHEETS)
            ),
            Worksheet("RawData", 20),
            Worksheet("Archive_2026_06", 21),
            Worksheet("Backup_RawData_test", 22),
        ]
        requests = build_tab_organization_requests(sheets)
        properties = [
            request["updateSheetProperties"]["properties"] for request in requests
        ]
        visible = [item for item in properties if not item["hidden"]]
        hidden = [item for item in properties if item["hidden"]]
        self.assertEqual([item["index"] for item in visible], list(range(5)))
        self.assertEqual({item["sheetId"] for item in hidden}, {20, 21, 22})

    def test_combined_verification_checks_counts_dates_and_latest_buildings(self):
        stats = build_combined_stats(
            {
                "RawData": [
                    [
                        "2026-09-14",
                        "อาคาร 7",
                        "กก1",
                        "กรุงเทพมหานคร",
                        "",
                        "กก1|กรุงเทพมหานคร",
                    ],
                    [
                        "2026-09-15",
                        "อาคาร 8",
                        "กก1",
                        "กรุงเทพมหานคร",
                        "",
                        "กก1|กรุงเทพมหานคร",
                    ],
                ]
            }
        )
        values = [
            ["ทะเบียนรถ+จังหวัด"],
            [
                "กก1|กรุงเทพมหานคร",
                "กก1",
                "กรุงเทพมหานคร",
                46279,
                46280,
                1,
                2,
                2,
                "อาคาร 7, อาคาร 8",
                "อาคาร 8",
                "ปกติ",
            ],
        ]
        verify_combined_values(values, stats)
        values[1][7] = 3
        with self.assertRaisesRegex(RuntimeError, "count mismatch"):
            verify_combined_values(values, stats)


if __name__ == "__main__":
    unittest.main()
