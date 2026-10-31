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

## Purple visual refinement - 31 October 2026

The supplied references combine compact mobile controls, layered graphite panels, restrained illuminated accents and a violet instrument-panel palette. The refinement keeps the existing registration workflow, six daily counters, top-right theme action, horizontal vehicle fields and equal-width Add/Clear controls.

Dark mode uses a near-neutral mauve charcoal (`#111015`), raised graphite panels (`#1d1b25`) and lavender accents (`#bda3ff`). Light mode uses a faint violet canvas (`#f5f2f9`), white panels and a deeper violet (`#7042b5`) for readable actions. Both native Streamlit palettes and custom CSS tokens are updated together. Green remains reserved for the actual last-read status, and red retains its error/cancellation meaning.

The daily total has a restrained violet gradient with a small decorative arc motif. Secondary counters use quieter surfaces and less repeated text. Navigation explicitly marks the current page; buttons, section markers, spacing and corners share the same visual system. Gradients are restricted to the total and primary action; there are no invented gauges, occupancy percentages, animated ambient backgrounds or data changes.

Research:
- [Radix scale roles](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale): separate canvas, surfaces, interaction states, borders and text by role.
- [Radix palette composition](https://www.radix-ui.com/colors/docs/palette-composition/composing-a-palette): pair violet accents with muted mauve neutrals and preserve distinct semantic status colors. These are custom project colors, not an unmodified Radix scale.
- [W3C text contrast](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html): check text against each adjacent surface and gradient stop. The chosen body, secondary, accent, total and primary-action text pairs exceed 4.5:1. The lowest checked pair is secondary light text on the tinted raised surface, at 4.52:1.

An important rendered check is button-label inheritance: the native Markdown wrapper must inherit the button foreground rather than forcing the page text color over the gradient. Local browser inspection confirms dark ink on the light lavender action in dark mode, and white text on the deeper violet action in light mode. Theme switching preserves a typed registration draft.

Rollback source checkpoint: `naccparking-pre-purple-checkpoint-20261031.zip`, commit `ac1f0abb2a664ba3f0e97c2ea0db7489874a6ec6`.
