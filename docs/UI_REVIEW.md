# UI consistency review — 11 October 2026

## Shared design contract

- `frontend/src/styles.css` is the single component-style source. Edit a component's existing rules rather than appending another visual override pass.
- The tokens at the top define colours, typography, radii and section spacing. Responsive rules are grouped at the bottom.
- Atkinson Hyperlegible is bundled under `frontend/public/fonts/`, including its OFL licence. Headings, body text, controls and evidence previews use this family; no external font service is required.
- Use `PageHeading` for secondary page introductions. Use the shared `card`, `panel`, `btn`, `choice`, `tag`, and `eyebrow` styles instead of independent equivalents.
- Body copy is 18px. Supporting copy is 16px; short metadata labels are 13px. Interactive controls are at least 48px tall. Warning meaning is conveyed in text as well as colour.
- Preserve the restored homepage content and the latest checking, OCR and moderation behavior when merging this change.

## Verification performed

- Production frontend build succeeded; 292 Python tests passed.
- Checked home, community, learning, sharing and moderation at 1440px, 390px and 320px. All used one font family and consistent heading sizes; no horizontal document overflow.
- Browser journeys on desktop and phone: empty input validation, mock offer analysis, evidence navigation, expanding findings, downloading a report, resetting, and guided analysis.
- Community: load, sorting, search with no matches, clear filters, category filters, navigation to learning and back to checking.
- Screenshot workflow: invalid file rejection and actual OCR of an invented investment screenshot, followed by reviewable extracted text.
- Story workflow: minimum length, outcome/type selection, redaction preview, required confirmations and successful submission to an isolated local SQLite database. No test stories submitted to the public deployment.
- Story preview and success state now receive focus and scroll into view. Reduced-motion preference is respected.
- No uncaught browser errors in the simulated journeys.

The public Render deployment was inspected as the baseline. Verification of the revised UI used the local preview; deployment still requires merging/deploying the fix branch.
