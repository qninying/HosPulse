import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

import { NextResponse } from "next/server";

import { parseUnsubscribeOutput } from "@/lib/unsubscribeOutcome";

const execFileAsync = promisify(execFile);

// Same split as api/upload/route.ts: process.cwd() is frontend/, one
// level up is the repo root where the Python venv and pipeline/ live.
const REPO_ROOT = path.join(process.cwd(), "..");
const PYTHON_BIN = path.join(REPO_ROOT, ".venv", "bin", "python3");
const UNSUBSCRIBE_SCRIPT = path.join(REPO_ROOT, "pipeline", "unsubscribe.py");
const SUBPROCESS_TIMEOUT_MS = 15_000;

type ExecError = Error & { stdout: string };

function isExecError(error: unknown): error is ExecError {
  return error instanceof Error && typeof (error as ExecError).stdout === "string";
}

// Compliance follow-up: the weekly briefing email's unsubscribe link
// points here. Deliberately never touches Supabase or the database
// directly -- UNSUBSCRIBE_SECRET and DATABASE_URL live only in the
// repo-root .env that the Python subprocess reads for itself, same
// boundary the upload route already established. Token verification
// (so a visitor can't unsubscribe someone else's address) happens
// entirely inside pipeline/unsubscribe.py, not here.
export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const company = url.searchParams.get("company");
  const email = url.searchParams.get("email");
  const token = url.searchParams.get("token");

  if (!company || !email || !token) {
    return NextResponse.redirect(new URL("/unsubscribed?ok=0", request.url));
  }

  let stdout: string;
  try {
    const result = await execFileAsync(
      PYTHON_BIN,
      [UNSUBSCRIBE_SCRIPT, "--company", company, "--email", email, "--token", token],
      { timeout: SUBPROCESS_TIMEOUT_MS, cwd: REPO_ROOT }
    );
    stdout = result.stdout;
  } catch (error) {
    // unsubscribe.py exits nonzero only on real server misconfiguration
    // (missing secret/DATABASE_URL) -- stdout still carries the JSON
    // result line in that case, same convention as the upload route.
    if (isExecError(error)) {
      stdout = error.stdout;
    } else {
      return NextResponse.redirect(new URL("/unsubscribed?ok=0", request.url));
    }
  }

  const outcome = parseUnsubscribeOutput(stdout);
  const ok = outcome.status === "unsubscribed" ? "1" : "0";
  return NextResponse.redirect(new URL(`/unsubscribed?ok=${ok}`, request.url));
}
