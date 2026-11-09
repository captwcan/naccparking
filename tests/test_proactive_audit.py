from datetime import date, datetime
from io import BytesIO
from unittest.mock import patch
import unittest

import pandas as pd
from openpyxl import load_workbook
from requests.exceptions import Timeout

from dashboard.data_service import prepare_dashboard_dataframe, to_csv_bytes, to_excel_bytes
from dashboard.home_summary import get_today_records
from report_generator import build_detailed_report, to_csv_bytes as report_csv
from report_generator import to_summary_pdf_bytes, to_summary_jpg_bytes
from services.archive_service import parse_parking_datetime
from services.google_sheets_service import cancel_parking_records
from test_app_smoke import Book
from unittest.mock import MagicMock
from dashboard import vehicle_analysis


class ProactiveAuditTests(unittest.TestCase):
    def test_rows_without_plate_do_not_inflate_counts_or_reports(self):
        from parking_analysis import summarize_long_parkers
        frame=pd.DataFrame([['2026-11-09','A',p,'ชลบุรี'] for p in [None,'']],
                            columns=['วันที่ตรวจพบ','อาคาร','ทะเบียนรถ','จังหวัด'])
        self.assertTrue(get_today_records(frame,date(2026,11,9)).empty)
        self.assertTrue(prepare_dashboard_dataframe(frame).empty)
        self.assertTrue(build_detailed_report(frame,'รายวัน',date(2026,11,9)).empty)
        self.assertTrue(summarize_long_parkers(frame,1).empty)
    def test_daily_weekly_monthly_pdf_and_jpg_exports_are_readable(self):
        from PIL import Image
        frame=pd.DataFrame([['2026-11-09','อาคาร 4','กก100','ชลบุรี']],
                            columns=['วันที่ตรวจพบ','อาคาร','ทะเบียนรถ','จังหวัด'])
        for mode in ['รายวัน','รายสัปดาห์','รายเดือน']:
            report=build_detailed_report(frame,mode,date(2026,11,9))
            pdf=to_summary_pdf_bytes(report,'รายงานทดสอบ',report_type=mode)
            self.assertTrue(pdf.startswith(b'%PDF-'))
            self.assertIn(b'%%EOF',pdf[-30:])
            image=Image.open(BytesIO(to_summary_jpg_bytes(report,'รายงานทดสอบ',report_type=mode)))
            self.assertEqual(image.format,'JPEG')
            image.verify()
    def test_vehicle_profile_and_timeline_escape_untrusted_markup(self):
        attack = '<img src=x onerror=alert(1)>'
        profile = dict(plate=attack,province=attack,total_seen=1,top_building=attack,
                       first_seen=date(2026,11,9),last_seen=date(2026,11,9),overnight_days=0)
        history=pd.DataFrame([{'วันที่ตรวจพบ':date(2026,11,9),'ทะเบียนรถ':attack,
                               'อาคาร':attack,'จังหวัด':attack,'is_overnight_candidate':False}])
        with patch.object(vehicle_analysis,'st') as ui:
            ui.columns.return_value=[MagicMock() for _ in range(5)]
            vehicle_analysis._render_profile(profile)
            vehicle_analysis._render_timeline(history)
        emitted=''.join(c.args[0] for c in ui.markdown.call_args_list)
        self.assertNotIn(attack,emitted)
        self.assertIn('&lt;img',emitted)
    def test_mixed_date_formats_are_consistent_in_summary_dashboard_and_report(self):
        dates = ['2026-11-09', '09/11/2026', '2026-11-09 01:30:00', 46335,
                 '2026-11-08T18:30:00+00:00']
        frame = pd.DataFrame([[d, 'อาคาร 4', f'กก{100+i}', 'ชลบุรี'] for i,d in enumerate(dates)],
                             columns=['วันที่ตรวจพบ','อาคาร','ทะเบียนรถ','จังหวัด'])
        target = date(2026,11,9)
        self.assertEqual(len(get_today_records(frame, target)), 5)
        self.assertEqual(set(prepare_dashboard_dataframe(frame)['วันที่ตรวจพบ']), {target})
        self.assertEqual(len(build_detailed_report(frame, 'รายวัน', target)), 5)

    def test_invalid_date_numbers_do_not_crash(self):
        for value in [float('inf'), float('nan'), 1e15, -1e15]:
            with self.subTest(value=value):
                self.assertIsNone(parse_parking_datetime(value))

    def test_report_uses_same_unicode_plate_normalization(self):
        frame = pd.DataFrame([['2026-11-09','A',p,'ชลบุรี'] for p in ['กก1234','กก—1234']],
                             columns=['วันที่ตรวจพบ','อาคาร','ทะเบียนรถ','จังหวัด'])
        self.assertEqual(len(build_detailed_report(frame,'รายวัน',date(2026,11,9))),1)

    def test_exported_text_cannot_become_a_spreadsheet_formula(self):
        frame = pd.DataFrame({'ทะเบียนรถ':['=1+1','+CMD','-CMD','@SUM(1)','\t=1+1','กก1234']})
        for export in [to_csv_bytes, report_csv]:
            parsed = pd.read_csv(BytesIO(export(frame)))
            self.assertTrue(parsed.iloc[0,0].startswith('\t'))
            self.assertTrue(parsed.iloc[4,0].startswith('\t'))
            self.assertEqual(parsed.iloc[-1,0],'กก1234')
        sheet = load_workbook(BytesIO(to_excel_bytes(frame))).active
        self.assertNotEqual(sheet['A2'].data_type,'f')
        self.assertEqual(sheet['A7'].value,'กก1234')
        self.assertEqual(frame.iloc[0,0],'=1+1')

    def test_cancel_recovers_after_commit_when_response_is_lost(self):
        book = Book()
        source=['2026-11-09','อาคาร 4','กก1','ชลบุรี']
        book.raw.rows[1]=source+['FORMULA']*9+['test-id']
        batch=[dict(zip(['date','building','plate','province'],source),record_id='test-id')]
        update=book.batch_update
        def commit_then_fail(body):
            update(body)
            raise Timeout('cancel committed; response lost')
        with patch.object(book,'batch_update',side_effect=commit_then_fail) as write:
            self.assertEqual(cancel_parking_records(book.raw,batch),1)
        self.assertEqual(write.call_count,1)
        self.assertEqual(book.raw.rows[1][:4],['']*4)
        self.assertEqual(book.raw.rows[1][4:13],['FORMULA']*9)
        self.assertEqual(cancel_parking_records(book.raw,batch),1)
