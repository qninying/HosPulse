# ADR-007: No frontend framework or component library

**Status:** Accepted

## Context

The frontend needed a real-looking operator dashboard (status cards, sparkline trends,
findings lists) as well as the earlier public Health Snapshot and upload pages. Tailwind, a
component library (e.g. shadcn/ui), and a charting library were all reasonable off-the-shelf
options.

## Decision

Plain, hand-written CSS (no Tailwind, no CSS modules), Server Components everywhere except the
one page that genuinely needs client interactivity (the upload page's live fetch/status), and a
hand-rolled inline-SVG sparkline instead of a charting dependency. `frontend/package.json` has
exactly four runtime dependencies: `@supabase/supabase-js`, `@supabase/ssr`, `next`, `react`
(+`react-dom`).

## Consequences

- Every dependency added is a real, deliberate one-line decision (matching the project's stated
  "no unnecessary dependencies" rule), not a batteries-included scaffold with mostly-unused
  surface area.
- The design brief's visual requirements (consistent card treatment, restrained styling, status
  colors) were satisfied with plain CSS custom properties and a handful of reusable React
  components (`Card`, `KpiCard`, `StatusCard`) — no framework was actually necessary to hit that
  bar.
- Cost: more hand-written CSS than a utility-class framework would require, and no design-token
  tooling beyond CSS custom properties. Judged acceptable at this project's current size (a
  handful of pages), worth revisiting if the frontend grows substantially.
- Tooltips use the native `title` attribute rather than a custom component, an explicit trade-off
  (accessible and free, but browser-styled) rather than adding a UI library for one feature.
