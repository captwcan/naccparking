import unittest
from unittest.mock import Mock
from datetime import date
import pandas as pd
from dashboard.data_service import prepare_dashboard_dataframe, CANONICAL_COLUMNS, VEHICLE_KEY_COL, OVERNIGHT_COL
from dashboard.metrics import compute_kpis, vehicle_options, vehicle_profile, vehicle_counts
from services.google_sheets_service import append_parking_rows, cancel_parking_records, GoogleSheetsService, read_all_parking_values
from services.workbook_organization_service import _verification_months


class AuditFixTests(unittest.TestCase):
    def sheet(self, values):
        sheet = Mock()
        sheet.id = 42
        sheet.title = 'RawData'
        sheet.row_count = 1000
        sheet.get.side_effect = lambda range: [r[:4] for r in values] if range == "A1:D" else [[r[13]] if len(r)>13 else [] for r in values]
        return sheet

    def test_different_provinces_do_not_merge_or_imply_overnight(self):
        frame = prepare_dashboard_dataframe(pd.DataFrame([
            ['2026-10-28', 'A', 'กก1234', 'กรุงเทพมหานคร'],
            ['2026-10-29', 'A', 'กก1234', 'ชลบุรี'],
        ], columns=CANONICAL_COLUMNS))
        self.assertEqual(compute_kpis(frame)['unique_vehicles'], 2)
        self.assertEqual(frame[OVERNIGHT_COL].sum(), 0)
        options = vehicle_options(frame, 'กก')
        self.assertEqual(len(options), 2)
        for option in options:
            self.assertEqual(len(vehicle_profile(frame, option)[1]), 1)

    def test_normalized_duplicates_rejected_before_writing(self):
        sheet = self.sheet([CANONICAL_COLUMNS, ['2026-10-29', 'A', 'กก1234', 'ชลบุรี']])
        with self.assertRaises(ValueError):
            append_parking_rows(sheet, [['2026-10-29', 'A', 'กก- 1234', 'ชลบุรี']])
        sheet.spreadsheet.batch_update.assert_not_called()

    def test_weekly_vehicle_counts_keep_provinces_separate(self):
        frame = prepare_dashboard_dataframe(pd.DataFrame([
            ['2026-10-27', 'A', 'กก1234', 'กรุงเทพมหานคร'],
            ['2026-10-28', 'A', 'กก-1234', 'กรุงเทพมหานคร'],
            ['2026-10-29', 'A', 'กก1234', 'ชลบุรี'],
        ], columns=CANONICAL_COLUMNS))
        counts = vehicle_counts(frame).set_index('จังหวัด')['จำนวนครั้ง'].to_dict()
        self.assertEqual(counts, {'กรุงเทพมหานคร': 2, 'ชลบุรี': 1})
        self.assertEqual(len(vehicle_options(frame, 'กก- 1234')), 2)

    def test_cancel_missing_item_does_not_partially_cancel_batch(self):
        row = ['2026-10-29', 'A', 'กก1234', 'ชลบุรี'] + ['']*9 + ['stable-id']
        sheet = self.sheet([CANONICAL_COLUMNS, row])
        item = dict(zip(['date','building','plate','province'], row[:4]), record_id='stable-id')
        with self.assertRaises(ValueError):
            cancel_parking_records(sheet, [item, dict(item, record_id='missing-id')])
        sheet.spreadsheet.batch_update.assert_not_called()

    def test_cancel_finds_id_after_row_shift_and_preserves_formulas(self):
        row = ['2026-10-29', 'A', 'กก1234', 'ชลบุรี'] + ['']*9 + ['stable-id']
        sheet = self.sheet([CANONICAL_COLUMNS, [], row])
        batch = [dict(zip(['date','building','plate','province'], row[:4]), record_id='stable-id')]
        self.assertEqual(cancel_parking_records(sheet, batch), 1)
        request = sheet.spreadsheet.batch_update.call_args.args[0]['requests'][0]['repeatCell']
        self.assertEqual(request['range']['startRowIndex'], 2)
        self.assertEqual(request['range']['endColumnIndex'], 4)

    def test_cancel_refuses_changed_record(self):
        row = ['2026-10-29', 'B', 'กก1234', 'ชลบุรี'] + ['']*9 + ['stable-id']
        sheet = self.sheet([CANONICAL_COLUMNS, row])
        with self.assertRaises(ValueError):
            cancel_parking_records(sheet, [dict(date='2026-10-29',building='A',plate='กก1234',province='ชลบุรี',record_id='stable-id')])
        sheet.spreadsheet.batch_update.assert_not_called()

    def test_archive_compaction_preserves_ids(self):
        book = Mock()
        book.worksheet.return_value.id = 42
        row = ['2026-10-29', 'A', 'กก1234', 'ชลบุรี'] + ['']*9 + ['stable-id']
        GoogleSheetsService(book).replace_source_columns('RawData', [row], clear_through_row_count=2)
        requests = book.batch_update.call_args.args[0]['requests']
        self.assertEqual(requests[1]['updateCells']['start']['columnIndex'], 13)
        self.assertEqual(requests[1]['updateCells']['rows'][0]['values'][0]['userEnteredValue']['stringValue'], 'stable-id')

    def test_empty_workbook_is_valid(self):
        plan = Mock()
        plan.months = [date(2026,10,1)]
        plan.month_stats = {plan.months[0]: Mock(period_days=0)}
        self.assertEqual(_verification_months(plan), ())

    def test_historical_rows_loaded_and_cancelled_rows_skipped(self):
        book = Mock()
        book.worksheets.return_value = [Mock(title='RawData'), Mock(title='Archive_2026_09'), Mock(title='Settings')]
        book.values_batch_get.return_value = {'valueRanges': [{'values':[CANONICAL_COLUMNS,[]]}, {'values':[CANONICAL_COLUMNS,['2026-09-01','A','กก1','ชลบุรี']]}]}
        result = read_all_parking_values(book)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1][0], '2026-09-01')

if __name__ == '__main__':
    unittest.main()
