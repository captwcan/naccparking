import json
import unittest
from unittest.mock import Mock, patch

import gspread
from requests import Response
from requests.exceptions import Timeout

from services.google_sheets_service import ParkingHTTPClient, append_parking_rows
from test_app_smoke import Book


def api_error(code):
    response = Response()
    response.status_code = code
    response._content = json.dumps({'error': {'code': code, 'message': 'simulated API failure'}}).encode()
    return gspread.exceptions.APIError(response)


class SaveServiceResilienceTests(unittest.TestCase):
    def test_transient_reads_back_off_and_recover(self):
        client = object.__new__(ParkingHTTPClient)
        response = Mock()
        with patch.object(gspread.HTTPClient, 'request', side_effect=[api_error(429), Timeout(), response]) as send, patch('services.google_sheets_service.time.sleep') as sleep, patch('services.google_sheets_service.random.random', return_value=0):
            self.assertIs(client.request('get', 'https://example.invalid/read'), response)
        self.assertEqual(send.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])

    def test_read_retries_are_bounded(self):
        client = object.__new__(ParkingHTTPClient)
        with patch.object(gspread.HTTPClient, 'request', side_effect=api_error(503)) as send, patch('services.google_sheets_service.time.sleep'):
            with self.assertRaises(gspread.exceptions.APIError):
                client.request('get', 'https://example.invalid/read')
        self.assertEqual(send.call_count, 4)

    def test_permission_failure_is_not_retried(self):
        client = object.__new__(ParkingHTTPClient)
        with patch.object(gspread.HTTPClient, 'request', side_effect=api_error(403)) as send, patch('services.google_sheets_service.time.sleep') as sleep:
            with self.assertRaises(gspread.exceptions.APIError):
                client.request('get', 'https://example.invalid/read')
        self.assertEqual(send.call_count, 1)
        sleep.assert_not_called()

    def test_write_timeout_is_never_blindly_replayed(self):
        client = object.__new__(ParkingHTTPClient)
        with patch.object(gspread.HTTPClient, 'request', side_effect=Timeout()) as send, patch('services.google_sheets_service.time.sleep') as sleep:
            with self.assertRaises(Timeout):
                client.request('post', 'https://example.invalid/write')
        self.assertEqual(send.call_count, 1)
        sleep.assert_not_called()

    def test_uncommitted_write_is_not_reported_as_success_or_replayed(self):
        book = Book()
        with patch.object(book, 'batch_update', side_effect=Timeout()) as write:
            with self.assertRaises(Timeout):
                append_parking_rows(book.raw, [['2026-11-09', 'อาคาร 4', 'กก1234', 'ชลบุรี']])
        self.assertEqual(write.call_count, 1)
        self.assertEqual(book.raw.rows[1][:4], [''] * 4)

    def test_readback_failure_preserves_original_uncertain_write_error(self):
        book = Book()
        original_get = book.raw.get
        read_count = 0
        def read_then_fail(range):
            nonlocal read_count
            read_count += 1
            if read_count > 2:
                raise RuntimeError('simulated readback failure')
            return original_get(range)
        error = Timeout('original write result unknown')
        with patch.object(book, 'batch_update', side_effect=error) as write, patch.object(book.raw, 'get', side_effect=read_then_fail):
            with self.assertRaises(Timeout) as raised:
                append_parking_rows(book.raw, [['2026-11-09', 'อาคาร 4', 'กก1234', 'ชลบุรี']])
        self.assertIs(raised.exception, error)
        self.assertEqual(write.call_count, 1)
