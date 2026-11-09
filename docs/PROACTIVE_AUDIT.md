# Proactive reliability audit - 9 November 2026

Baseline: `5b7ed196b9aa2b8fd71b17da1166d8a20adcb1d6`.
Checkpoint: `naccparking-pre-audit-20261109.zip`.

## Reproduced and repaired

| Area | Reproduction | Result |
| --- | --- | --- |
| Date consistency | ISO, Thai day/month, datetime, spreadsheet serial and UTC-offset cells in one dataset | Shared Bangkok parser now gives the same records to the daily summary, dashboard, long-parking analysis and reports |
| Invalid date cells | Infinity, NaN and out-of-range serials raised exceptions | Invalid values return no date and are excluded/reported without crashing |
| Vehicle identity | Unicode dash variant created two report vehicles | Reports and long-parking analysis use the shared plate normalizer |
| Incomplete rows | A date with no plate inflated summary/report counts | Plate-less rows are excluded consistently |
| Draft preservation | Reducing the requested row count immediately deleted a filled tail row | Filled rows remain until explicit reduction confirmation |
| Settings outage | A Settings read failure raised an unhandled page exception | Friendly retry and preserved drafts instead of page failure |
| Empty report dates | Clearing a report date produced an exception | Date prompt/no filter handles empty dates |
| Cancellation acknowledgement | Google cleared A:D, then a simulated response timeout occurred | UUID readback confirms cancellation; repeated cancellation is a no-op |
| Exported input | A user string beginning with `=` became an XLSX formula | XLSX text is explicitly string typed; CSV formula-leading text is quoted and tab-prefixed |
| Untrusted HTML | Vehicle profile/timeline interpolated raw building/plate/province markup | User-controlled text is escaped |
| Stale archive plan | A new record added after planning could be overwritten by compaction | Preflight rejects changed source cells/IDs before backup/archive writes |
| Dependency drift | Most top-level dependencies were floating | Direct versions now match the tested environment, compatible with Python 3.11+ |

The audit regression log records the original failures. The suite covers recording, backdating, duplicate protection, save/cancel, 40-row quota pressure, 100-row drafts, all dashboard sections, changing report month, clearing dates, daily/weekly/monthly PDF/JPG creation, CSV/XLSX literal text and stale archive plans. No destructive maintenance operation was executed on the production workbook for this audit.

Dependency scan: `pip-audit -r requirements.txt` resolved and checked the pinned requirements with no known vulnerabilities reported at scan time. This is advisory database evidence for the resolved package set; it is not a guarantee of the deployed environment's full security. Versions and results are retained in `audit-dependencies-pinned.json`.

CSV mitigation follows [OWASP CSV Injection](https://community.owasp.org/attacks/CSV_Injection). CSV consumer behavior varies; XLSX exports explicitly retain string cell types. Source data is not rewritten by export.

## Important remaining risks

1. **Public workbook editing:** current Drive permissions include `anyone: writer`. Restricting that access preserves the owner, BW Codex and app service account, but affects direct link editors; it requires the owner's access choice. The app's server-side service account already has explicit writer permission.
2. **Administration/report access:** building administration is not protected by authentication and report access uses a public source-code password. A real administrator identity/allowlist and server-side secrets are needed. This audit does not guess the authorized staff accounts or silently change their workflow.
3. **Concurrent external maintenance:** preflight prevents using a stale plan at the start. Archive compaction still spans several API requests and is not a transaction with Streamlit writes/cancellations. Run it in a quiet maintenance window; full concurrent safety requires coordinated maintenance or a transactional datastore. The new preflight does not claim to solve a writer arriving later in the migration.
4. **External outages:** bounded retries and preserved drafts reduce failure impact. They cannot remove Google availability, quota or permission failures. Cancellation readback retains the original error if completion cannot be verified.

These remaining items are explicitly separated from the tested repairs; this release does not claim that the site can never fail again.
