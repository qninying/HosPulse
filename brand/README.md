# HosPulse brand assets

- `logo.svg` — full lockup (icon + wordmark), for **light backgrounds**: README, one-pagers, light-themed decks.
- `logo-on-dark.svg` — same lockup, for **dark/navy backgrounds**: the Command Center header, dark hero sections.
- `icon.svg` — mark only, teal square with the pulse line. Works on any background. Used as the favicon everywhere and in the Command Center header.

Colors: navy `#0F2A44`, teal `#13A39A`, light teal `#5FD4CB` (wordmark accent on dark only). These match `command-center/assets/command-center.css`'s `--cc-brand`/`--cc-accent` tokens and `project-blueprint/mockup.html` / `one-pager.html`.

When making a new document or artifact that needs the mark, reference these files rather than redrawing the icon by hand — that's what went wrong before this file existed: the same SVG was hand-copied into 9 Command Center pages. In a GitHub-rendered Markdown file, use the `<picture>` pattern so it survives GitHub's own dark mode:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="brand/logo-on-dark.svg">
  <img alt="HosPulse" src="brand/logo.svg" height="44">
</picture>
```

In a standalone HTML page or PDF (a one-pager, a slide), inline whichever variant matches that page's own background — an external file reference doesn't survive being rendered to a static image/PDF by itself, so copy the relevant `<svg>...</svg>` contents in directly.
