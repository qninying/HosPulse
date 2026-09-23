// STORY-005: real browser E2E coverage for the operator upload page --
// drives an actual headless Chromium browser against the running Next.js
// app, exercising the full stack (page -> API route -> Python subprocess
// -> Supabase), not a mocked handler. Complements the pure unit tests in
// src/lib/exportUpload.test.ts, which cover the parsing logic without a
// browser or a live database.
import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { promisify } from "node:util";

import { expect, test } from "@playwright/test";

const execFileAsync = promisify(execFile);
const REPO_ROOT = path.join(__dirname, "..", "..");
const PYTHON_BIN = path.join(REPO_ROOT, ".venv", "bin", "python3");

// A real hospital already in the `hospitals` table (STORY-001's CMS
// import) -- the upload path's foreign key on provider_ccn requires a
// real CCN, not a made-up one.
const REAL_PROVIDER_CCN = "370178";

test.describe("operator upload page", () => {
  const sourceFile = `e2e-upload-${randomUUID()}.csv`;
  // A value unique to this test run, so re-running the suite doesn't
  // collide with a prior run's file hash and get treated as a duplicate
  // before the "fresh upload" test even gets to assert that outcome.
  const uniqueCash = 100000 + (Date.now() % 100000);
  const csvContent =
    "hospital_ccn,report_month,line_type,cash_balance,net_ar_balance,denied_claims,total_claims,open_fte_positions\n" +
    `${REAL_PROVIDER_CCN},2026-09-01,DATA,${uniqueCash},320000,12,200,3\n`;

  test.afterAll(async () => {
    // Cleans up this run's rows so the suite leaves no residue in the
    // shared Supabase database -- same rule this project's manual live
    // verifications already follow (see PROGRESS.md).
    const script = `
import os, sys
sys.path.insert(0, "pipeline")
from pathlib import Path
from env import load_env
load_env(Path(${JSON.stringify(REPO_ROOT)}) / ".env")
import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=10)
cur = conn.cursor()
cur.execute("DELETE FROM hospital_monthly_metrics WHERE source_file = %s", (${JSON.stringify(sourceFile)},))
cur.execute("DELETE FROM export_conversions WHERE source_file = %s", (${JSON.stringify(sourceFile)},))
conn.commit()
conn.close()
`;
    await execFileAsync(PYTHON_BIN, ["-c", script], { cwd: REPO_ROOT });
  });

  test("uploading a valid export shows an accepted message", async ({ page }) => {
    await page.goto("/upload");
    await expect(
      page.getByRole("heading", { name: "Upload a monthly export" })
    ).toBeVisible();

    await page.setInputFiles('input[type="file"]', {
      name: sourceFile,
      mimeType: "text/csv",
      buffer: Buffer.from(csvContent),
    });
    await page.getByRole("button", { name: "Upload" }).click();

    await expect(page.getByText(/metrics normalized/)).toBeVisible({ timeout: 15_000 });
  });

  test("uploading the identical file again shows a duplicate message", async ({ page }) => {
    await page.goto("/upload");
    await page.setInputFiles('input[type="file"]', {
      name: sourceFile,
      mimeType: "text/csv",
      buffer: Buffer.from(csvContent),
    });
    await page.getByRole("button", { name: "Upload" }).click();

    await expect(page.getByText(/duplicate/i)).toBeVisible({ timeout: 15_000 });
  });

  test("uploading a PHI-bearing export is rejected, not silently accepted", async ({ page }) => {
    // No cleanup needed for this file: a PHI rejection never writes to
    // export_conversions or hospital_monthly_metrics at all (verified in
    // STORY-011/STORY-005's live testing) -- there is nothing to delete.
    const phiSourceFile = `e2e-upload-phi-${randomUUID()}.csv`;
    const phiContent =
      "hospital_ccn,report_month,line_type,cash_balance,net_ar_balance,denied_claims,total_claims,open_fte_positions,Patient Name\n" +
      `${REAL_PROVIDER_CCN},2026-10-01,DATA,150000,320000,12,200,3,Jane Doe\n`;

    await page.goto("/upload");
    await page.setInputFiles('input[type="file"]', {
      name: phiSourceFile,
      mimeType: "text/csv",
      buffer: Buffer.from(phiContent),
    });
    await page.getByRole("button", { name: "Upload" }).click();

    await expect(page.getByText(/rejected/i)).toBeVisible({ timeout: 15_000 });
  });
});
