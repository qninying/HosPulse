import { execFile } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";

import { NextResponse } from "next/server";

import {
  httpStatusFor,
  messageFor,
  parseNormalizerOutput,
  type UploadOutcome,
} from "@/lib/exportUpload";

const execFileAsync = promisify(execFile);

// process.cwd() is the frontend/ directory (where `next dev`/`next start`
// runs from) -- one level up is the repo root, where the Python venv and
// pipeline/ live.
const REPO_ROOT = path.join(process.cwd(), "..");
const PYTHON_BIN = path.join(REPO_ROOT, ".venv", "bin", "python3");
const NORMALIZER_SCRIPT = path.join(REPO_ROOT, "pipeline", "export_normalizer.py");
const SUBPROCESS_TIMEOUT_MS = 30_000;

type ExecError = Error & { stdout: string; code: number | null };

function isExecError(error: unknown): error is ExecError {
  return error instanceof Error && typeof (error as ExecError).stdout === "string";
}

// STORY-005: accepts an operator's monthly export, hands it to the
// already-built, already-tested Python normalizer (STORY-011) as a
// subprocess, and reports the real outcome -- accepted, duplicate,
// needs_mapping, or rejected -- with no logic reimplemented here. Never
// touches Supabase directly: DATABASE_URL lives only in the repo-root
// .env that the Python subprocess reads for itself, never in this
// Node process's environment or the browser bundle.
export async function POST(request: Request): Promise<Response> {
  let file: FormDataEntryValue | null;
  try {
    const formData = await request.formData();
    file = formData.get("file");
  } catch {
    // An empty body or a Content-Type that isn't multipart form data
    // throws inside request.formData() itself, before any of our own
    // validation runs -- found live via a curl request with no file
    // attached at all, which otherwise surfaced as an unhandled 500
    // with no body instead of a clean 400.
    return NextResponse.json(
      { status: "error", message: "Request body could not be read as multipart form data." },
      { status: 400 }
    );
  }

  if (!(file instanceof File)) {
    return NextResponse.json(
      { status: "error", message: "No file was provided." },
      { status: 400 }
    );
  }

  const tmpDir = await mkdtemp(path.join(tmpdir(), "hospulse-upload-"));
  const tmpPath = path.join(tmpDir, file.name || "export.csv");

  try {
    const buffer = Buffer.from(await file.arrayBuffer());
    await writeFile(tmpPath, buffer);

    let stdout: string;
    try {
      const result = await execFileAsync(
        PYTHON_BIN,
        [NORMALIZER_SCRIPT, "--json", tmpPath],
        { timeout: SUBPROCESS_TIMEOUT_MS, cwd: REPO_ROOT }
      );
      stdout = result.stdout;
    } catch (error) {
      // export_normalizer.py --json exits nonzero for failed/phi_rejected
      // outcomes, which makes execFile reject -- its stdout still carries
      // the JSON result line, so this is not necessarily a crash.
      if (isExecError(error)) {
        stdout = error.stdout;
      } else {
        throw error;
      }
    }

    const outcome: UploadOutcome = parseNormalizerOutput(stdout, 0);
    return NextResponse.json(
      { status: outcome.status, message: messageFor(outcome) },
      { status: httpStatusFor(outcome) }
    );
  } catch (error) {
    return NextResponse.json(
      {
        status: "error",
        message: error instanceof Error ? error.message : "Unexpected upload error",
      },
      { status: 500 }
    );
  } finally {
    await rm(tmpDir, { recursive: true, force: true });
  }
}
