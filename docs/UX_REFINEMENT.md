# Mobile UX release

Production checkpoint: Full Release, commit 6fc963fe7839f943957ad824fe35beaeee06bce4.
The user approved publication on 29 October 2026 after reviewing the mobile preview and final layout changes.

## Requirements retained

- Existing Streamlit application, daily registration workflow, province selection and Google Sheet schema.
- Existing save, duplicate validation, UUID cancellation, historical dashboard and report exports.
- Building names and production database contents are unchanged.

## Reference decisions

- [Linear: A calmer interface](https://linear.app/now/behind-the-latest-design-refresh): reduce competing borders/icons, keep work and navigation visually distinct, use consistent muted surfaces and typography.
- [Carbon status indicators](https://v10.carbondesignsystem.com/patterns/status-indicator-pattern/): communicate status with text and meaningful symbols as well as color. Change badges represent actual count differences; no arbitrary occupancy goals or invented percentages.
- [GOV.UK text input](https://design-system.service.gov.uk/components/text-input/): keep visible labels and preserve answers when validation fails.
- [Streamlit fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment): refresh only the summary while the browser session is active, preserving the registration draft.

## Final requested layout

- Summary above the form, including the total and all five existing building counters.
- Six compact cards in three columns on phones; total is first and visually emphasized.
- Honest last-read time, 30-second active-session refresh, and count-change feedback.
- Refresh control inside the summary panel at the lower right.
- Full-width batch size control, followed by Add / Clear in two equal columns on phones.
- Plate / Province / Remove on one horizontal row even on phones.
- Registration and building drafts survive a dashboard visit.
- Neutral graphite / soft green dark theme and corresponding light theme with IBM Plex Sans Thai.

## Review and validation

Local sample preview: http://127.0.0.1:8507
The preview launcher uses an in-memory workbook and explicitly labels the sample data. It never connects to or writes parking records to the production workbook.
Regression tests cover save/cancel, real count-change feedback, manual summary refresh, draft preservation, 40-row entry and 100-row entry.
Visual inspection was performed in Edge at a 440px mobile viewport. The compact row and equal-width buttons were verified in the rendered UI. The regression suite also exercises light-mode state, 40-row and 100-row drafts. Pixel verification is limited to the observed 440px mobile viewport.

Local rollback: restore the Full Release source ZIP. The release updates application source only; it requires no parking-data or schema migration.

## Theme consistency follow-up

The former toggle changed application CSS while Streamlit retained a single light native theme. Native widgets, calendar overlays, canvas dataframes and charts could therefore disagree with the selected mode.

Both native theme variants now use the same palette as the application tokens in `.streamlit/config.toml`. The visible theme button is at the upper right of the header on both pages. It selects Streamlit's native theme in the current browser session without reloading the page or rewriting server config. Drafts survive switching themes and pages.

`dashboard/theme_sync.js` uses Streamlit 1.66.1's native theme menu controls, identified by `stMainMenuButton` and `stMainMenuItem-theme-Light` / `stMainMenuItem-theme-Dark`. The package is pinned to that version. Recheck those controls, both modes, calendars and canvas tables when upgrading Streamlit. The regular native menu theme choices are hidden so the application has one theme control.

References: [native light/dark configuration](https://docs.streamlit.io/develop/concepts/configuration/theming), [Streamlit 1.66.1 theme selection](https://github.com/streamlit/streamlit/blob/1.66.1/frontend/app/src/components/MainMenu/themeSection.ts), [trusted JavaScript in st.html](https://docs.streamlit.io/develop/api-reference/text/st.html).

Follow-up checks cover desktop dark/light widgets and charts, a dark calendar overlay and raw-data canvas table, and the 390px mobile header and registration form. No production parking records are written by these checks.
