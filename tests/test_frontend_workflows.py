from unittest.mock import Mock, patch
import unittest
import streamlit as st
from streamlit.testing.v1 import AppTest
from test_app_smoke import APP, Book


class FrontendWorkflowTests(unittest.TestCase):
    def setUp(self):
        st.cache_resource.clear()
        st.cache_data.clear()
        self.book = Book()
        client = Mock()
        client.open_by_url.return_value = self.book
        for patcher in (patch('gspread.authorize', return_value=client), patch('google.oauth2.service_account.Credentials.from_service_account_info', return_value=Mock())):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.app = AppTest.from_file(APP)
        self.app.secrets['gcp_service_account'] = {}
        self.app.secrets['spreadsheet_url'] = 'https://example.invalid/fixture'
        self.app.run(timeout=30)

    def button(self, label):
        return next(item for item in self.app.button if item.label == label)

    def plates(self):
        return [item for item in self.app.text_input if item.label == 'ทะเบียนรถยนต์']

    def test_add_and_theme_change_preserve_draft(self):
        self.plates()[0].input('กก1234'); self.app.run()
        self.button('➕ เพิ่มทะเบียน').click(); self.app.run()
        self.assertEqual(len(self.plates()), 2)
        self.app.toggle[0].set_value(False); self.app.run()
        self.assertEqual(self.plates()[0].value, 'กก1234')
        self.assertEqual(self.app.session_state.ui_theme, 'light')
        self.assertFalse(self.app.exception)

    def test_clear_requires_confirmation(self):
        self.plates()[0].input('กก1234'); self.app.run()
        self.button('ล้างรายการ').click(); self.app.run()
        self.assertEqual(self.plates()[0].value, 'กก1234')
        self.button('ยืนยันล้างรายการ').click(); self.app.run()
        self.assertEqual(len(self.plates()), 1)
        self.assertEqual(self.plates()[0].value, '')
        self.assertFalse(self.app.exception)

    def test_duplicate_variants_disable_save(self):
        self.plates()[0].input('กก1234'); self.app.run()
        self.button('➕ เพิ่มทะเบียน').click(); self.app.run()
        self.plates()[1].input('กก- 1234'); self.app.run()
        self.assertTrue(self.button('💾 บันทึกข้อมูลเข้าสู่ระบบ').disabled)
        self.assertTrue(any('ซ้ำ' in warning.value for warning in self.app.warning))

    def test_blank_input_cannot_submit(self):
        self.assertTrue(self.button('💾 บันทึกข้อมูลเข้าสู่ระบบ').disabled)

    def test_large_batch_and_theme_keep_values(self):
        self.plates()[0].input('กก1234'); self.app.run()
        next(item for item in self.app.number_input if item.label == 'จำนวนทะเบียนที่จะบันทึก').set_value(100)
        self.app.run(timeout=30)
        self.assertEqual(len(self.plates()), 100)
        self.assertEqual(self.plates()[0].value, 'กก1234')
        self.assertFalse(self.app.exception)

    def test_history_filters_and_reset(self):
        self.book.raw.rows += [
            ['2026-10-29', 'อาคาร 4', 'กก1234', 'กรุงเทพมหานคร'],
            ['2026-10-29', 'อาคาร 4', 'กก1234', 'ชลบุรี'],
        ]
        self.app.switch_page('pages/dashboard.py'); self.app.run(timeout=30)
        self.assertFalse(self.app.exception)
        self.app.get('segmented_control')[0].set_value('raw'); self.app.run(timeout=30)
        next(w for w in self.app.multiselect if w.label == 'จังหวัด').set_value(['ชลบุรี']); self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any('1 รายการ' in c.value for c in self.app.caption))
        self.button('ล้างตัวกรอง').click(); self.app.run()
        self.assertEqual(next(w for w in self.app.multiselect if w.label == 'จังหวัด').value, [])
        self.assertFalse(self.app.exception)

    def test_connection_failure_has_distinct_message(self):
        st.cache_data.clear()
        with patch.object(self.book, 'values_batch_get', side_effect=RuntimeError('simulated unavailable')):
            self.app.run()
            self.assertFalse(self.app.exception)
            self.assertTrue(any('ไม่สามารถโหลดข้อมูลสรุปวันนี้' in m.value for m in self.app.markdown))
