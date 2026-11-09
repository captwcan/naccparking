# Parking save reliability - 9 November 2026

The production workbook was readable and a clearly identified diagnostic record saved successfully. A universal loss of write permission was therefore not reproduced. Three failure patterns were reproduced in the browser or isolated application tests:

- The first plate input held an uncommitted value while Save remained disabled. Typing and clicking Save required leaving the field first.
- A 40-row draft with plate/province edits repeatedly fetched Settings. A quota-limited fixture failed with HTTP 429 before the batch could be saved.
- A simulated Google write committed the row, then lost its response. The app displayed a save failure despite the stored record.

Save now validates the submitted values instead of gating the button on previously committed text. Blank, duplicate and invalid-date records still cannot be written. Successful saves retain the receipt/cancel metadata and start a blank draft so the previous batch is not accidentally resubmitted.

Building names are cached for five minutes across reruns; admin edits invalidate that cache immediately. The recording client retries transient GET failures with bounded exponential backoff and jitter. It does not replay POST writes. When a write response is uncertain, the service checks the generated immutable IDs and exact source values before returning success. An unconfirmed write still raises the original error.

References: [Google Sheets quotas and backoff](https://developers.google.com/workspace/sheets/api/limits), [gspread HTTP client](https://docs.gspread.org/en/latest/api/http_client.html).

Validation covers a quota-limited 40-row entry sequence, first-click browser save without Tab/Enter, uncertain committed/uncommitted writes, bounded read retries, permission failures, duplicate/empty submissions, fresh successive batches and admin cache invalidation. The complete suite includes the existing backdated-save/cancel and formula-preservation checks. The pre-change source checkpoint is `naccparking-pre-save-fix-20261109.zip` at `d8c6c8b1ca201fefd4dd3245ec7ed499b9f41c9a`.

Production verification must identify each synthetic record, read its stored date/plate/UUID back from RawData, cancel only that batch through the app, and verify A:D is empty afterward. Existing user records and E:M formula anchors must be preserved. The retained UUID is the existing cancellation audit behavior, not an active parking record.
