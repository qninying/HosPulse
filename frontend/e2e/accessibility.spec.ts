// Compliance follow-up item 7: an actual automated contrast check against
// the real rendered pages and the real palette, not a manual eyeball of
// hex values. Uses axe-core (the same engine Lighthouse's accessibility
// audit is built on) against every public, pre-auth page -- the
// authenticated dashboard pages require a real session and aren't
// reachable here, a known limitation, not an oversight.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const PUBLIC_PAGES = [
  "/",
  "/privacy",
  "/terms",
  "/login",
  "/upload",
  "/unsubscribed?ok=1",
  "/unsubscribed?ok=0",
  // These query-param states render .hp-alert-danger, which never
  // appears during ordinary navigation -- the eyebrow/button/ok-alert
  // failures axe first found were only caught because those render
  // unconditionally; a state that only shows on error is just as real
  // and just as easy to silently ship broken if nothing ever renders it.
  "/login?error=Something%20went%20wrong",
];

for (const path of PUBLIC_PAGES) {
  test(`${path} has no color-contrast violations (light mode)`, async ({ page }) => {
    await page.goto(path);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2aa"])
      .include("body")
      .analyze();

    const contrastViolations = results.violations.filter((v) => v.id === "color-contrast");
    if (contrastViolations.length > 0) {
      console.log(JSON.stringify(contrastViolations, null, 2));
    }
    expect(contrastViolations).toEqual([]);
  });

  test(`${path} has no color-contrast violations (dark mode)`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto(path);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2aa"])
      .include("body")
      .analyze();

    const contrastViolations = results.violations.filter((v) => v.id === "color-contrast");
    if (contrastViolations.length > 0) {
      console.log(JSON.stringify(contrastViolations, null, 2));
    }
    expect(contrastViolations).toEqual([]);
  });
}
