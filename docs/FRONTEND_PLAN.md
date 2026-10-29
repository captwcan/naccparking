# NACC Parking frontend implementation plan

Prepared: 2026-10-29 (Asia/Bangkok)
Source: captwcan/naccparking, production UI and commit 0a078265ed036422b8d5b144152f72000fa6f078.

## Scope and current delivery status

This release applies the supplied frontend and audit fixes to the production repository. It also keeps weekly vehicle counts separate by province and prevents partial cancellation when any record in a saved batch is missing. The local regression suite passes 74 tests with Streamlit 1.66.1. A manually dispatched CI job checks both pages against the existing production workbook with read-only operations.

Authentication and Google Sheet sharing permissions remain unchanged and require separate follow-up.

## Observed issues

- Dark-mode section headings and some form labels have very low contrast. The theme module defines --text-main, while later page CSS overrides section headings using --text-color.
- Theme styles are duplicated in the page, shared theme module, dashboard styles and summary markup. Widget updates rerun the page, making consistent theming and retained input state important.
- A large hero and six summary cards occupy most of the first viewport before data entry begins.
- Each additional registration produces a separate block and pushes Save farther down the page.
- Main actions, secondary actions and destructive actions need clearer hierarchy. Save currently uses the default red accent.
- Dashboard/report navigation lives in a collapsed admin sidebar. No-data and invalid-date states are combined in one message.

## Implementation sequence

### 1. Theme and component foundation

Files: dashboard/theme.py, dashboard/styles.py, dashboard/home_summary.py, app_parking.py.

Use one set of color, typography, spacing and border tokens. Remove conflicting page overrides. Apply tokens to labels, headings, inputs, dropdown menus, focus rings, buttons and status messages. Use readable Thai type and a restrained navy/teal identity. Reserve danger styling for cancellation/removal. Ensure the selected theme remains consistent when navigating to the dashboard.

Acceptance: labels and controls remain readable in both themes, including expanded selects, disabled controls and keyboard focus. Switching theme preserves unsaved registration rows.

### 2. Recording page layout

Files: app_parking.py, dashboard/home_summary.py.

Replace the tall hero with a compact title, Bangkok business date and clear navigation to Recording, History and Reports. Show a compact total and expandable building breakdown. Prioritize building selection and the first registration field. Use a wider desktop layout with the form and today's summary beside one another; stack content on narrow screens.

Acceptance: the first registration field is reachable without traversing a full dashboard. No horizontal page scrolling at 360px width. A user can reach primary navigation without opening an admin panel.

### 3. Multi-registration entry and feedback

Files: app_parking.py and shared UI components.

Keep a searchable building/province selection and an explicit province for each registration. Use compact rows on desktop and cards on mobile. Place Add registration beside the list and keep a clearly visible Save action with the number of valid registrations. Show validation next to the affected row, normalize identity through the existing shared domain code, and preserve user-entered display text. Make row removal and clearing the whole unsaved batch distinct. Confirm clearing a nonempty batch. Show loading/submitting states, disable repeated submission while running, and show a success receipt containing building, Bangkok date and saved count. Cancellation should refer to the saved batch and use its immutable record IDs.

Acceptance: entry works with 1, 20 and 100 rows; duplicate detection identifies the affected rows; theme changes and adding a row do not erase existing input; success, failure and retry states are distinguishable.

### 4. History, dashboard and report navigation

Files: pages/dashboard.py, dashboard/period_analysis.py, dashboard/raw_data.py, dashboard/vehicle_analysis.py, dashboard/components.py, dashboard/metrics.py.

Provide a clear filter bar for date range/month, building and province, with reset and result count. Display vehicle identity with both plate and province. Place export actions next to the results and show the selected period and record count before downloading. Use compact summaries on narrow screens and a detail view for a selected vehicle. Keep empty database, empty filter result, data-load failure and invalid-row warnings separate.

Acceptance: archived months are selectable; identical registrations from different provinces remain distinct in search and detail views; exported data follows the visible filter; no successful empty state is presented as a connection error.

### 5. Verification and release

Test desktop and narrow layouts at 360, 390, 768 and 1440px widths, both themes, keyboard operation, long Thai labels, empty results, service failures and slow submission. Extend AppTest around input preservation and filter behavior. Run the existing 65 regression tests. Test writes only against an isolated workbook or in-memory fixture. Release the existing audit fixes separately from frontend work so each change can be verified and reverted independently.

Suggested commits:

1. fix(ui): unify theme colors and readable form labels
2. feat(ui): prioritize parking entry and compact daily summary
3. feat(ui): improve batch entry validation and save feedback
4. feat(ui): add clear history filters and report actions
5. test(ui): cover responsive workflows and retained form state

## Proposed completion criteria

- No unreadable text in either theme.
- No clipped primary actions or horizontal page overflow at the target widths.
- Every registration retains its province and input value during interaction.
- Saving and cancelling a batch preserve Google Sheets formula anchors.
- Users can tell when data is loading, saved, empty or unavailable.
- Existing parking/report behavior remains covered by passing regressions.

## Remaining external requirement

Enable the ChatGPT GitHub integration for captwcan/naccparking with the repository write capability needed for the approved commit and deployment. Do not request another approval for the already-authorized release; resolve the connection capability, then publish and verify the deployed version.


## Implementation update

Frontend implementation is included in this package. Changes cover shared theme styles, compact header and daily total, top-level navigation, registration cards, inline duplicate warnings, disabled invalid submission, clear/cancellation confirmation, persistent last-batch receipt, history sections, filter reset, export range/count labels, and distinct no-data/load-failure messages. The tested Streamlit release is pinned to 1.66.1 and sizing APIs use width instead of deprecated use_container_width.

Validation: 72 tests passed with real installed dependencies, including AppTest save/cancel, preserving draft through theme and row changes, 100-row input, duplicate prevention, filter/reset and simulated connection failure. Runtime code parses successfully.

Visual limitation: the cloud browser cannot reach this executor's local preview server (connection refused). The new layout has not been visually verified at the target viewport sizes or deployed to production. CSS includes small-screen layout rules; a real-browser visual pass remains required.

GitHub confirms the user's repository permissions include push=true. The integration's create-branch request still returns 403 Resource not accessible by integration. Collaborator access is present; the integration token's effective write capability remains the blocker. Publication is approved. No application code has been committed remotely or deployed.
