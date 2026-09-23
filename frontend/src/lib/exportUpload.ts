// STORY-005: bridges the operator upload route to the already-built,
// already-tested Python normalizer (pipeline/export_normalizer.py,
// STORY-011) via subprocess rather than reimplementing hash-dedup,
// format detection, or the PHI gate in TypeScript. This file holds only
// the pure piece of that bridge -- parsing the subprocess's `--json`
// output into a typed outcome -- so it's unit-testable without spawning
// a real process. The route handler (app/api/upload/route.ts) does the
// actual spawning and is verified live instead, same split the Python
// side uses between pure and DB-wired functions.

export type UploadOutcome =
  | { status: "ok"; sourceSystem: string; metricsCount: number }
  | { status: "duplicate"; sourceSystem: string | null }
  | { status: "needs_mapping" }
  | { status: "phi_rejected"; message: string }
  | { status: "failed"; message: string }
  | { status: "error"; message: string };

// export_normalizer.py's PHI gate logs a structured JSON audit line to
// stdout via print() *before* returning (see _log_phi_audit), and the
// __main__ block's own --json result line is always printed last, after
// run() returns. So stdout can be more than one JSON line -- the real
// result is reliably the last one, not necessarily the only one.
export function parseNormalizerOutput(
  stdout: string,
  exitCode: number
): UploadOutcome {
  const lines = stdout.split("\n").map((l) => l.trim()).filter(Boolean);
  const lastLine = lines[lines.length - 1];
  if (!lastLine) {
    return { status: "error", message: `no output from normalizer (exit ${exitCode})` };
  }

  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(lastLine);
  } catch {
    return { status: "error", message: `unparseable normalizer output: ${lastLine}` };
  }

  if (parsed.status === "phi_rejected") {
    return { status: "phi_rejected", message: String(parsed.message ?? "PHI detected") };
  }
  if (parsed.is_duplicate === true) {
    return {
      status: "duplicate",
      sourceSystem: (parsed.source_system as string | null) ?? null,
    };
  }
  if (parsed.status === "ok") {
    return {
      status: "ok",
      sourceSystem: String(parsed.source_system ?? "unknown"),
      metricsCount: Number(parsed.metrics_count ?? 0),
    };
  }
  if (parsed.status === "needs_mapping") {
    return { status: "needs_mapping" };
  }
  if (parsed.status === "failed") {
    return { status: "failed", message: String(parsed.error_message ?? "conversion failed") };
  }
  return { status: "error", message: `unrecognized normalizer status: ${lastLine}` };
}

export function httpStatusFor(outcome: UploadOutcome): number {
  switch (outcome.status) {
    case "ok":
      return 200;
    case "duplicate":
      return 409;
    case "needs_mapping":
    case "phi_rejected":
    case "failed":
      return 422;
    case "error":
      return 500;
  }
}

export function messageFor(outcome: UploadOutcome): string {
  switch (outcome.status) {
    case "ok":
      return `Accepted: ${outcome.metricsCount} metrics normalized from a ${outcome.sourceSystem} export.`;
    case "duplicate":
      return "This exact file was already uploaded and processed -- duplicate rejected.";
    case "needs_mapping":
      return "Unrecognized export format -- marked as needs mapping, no metrics were guessed.";
    case "phi_rejected":
      return `Rejected: ${outcome.message}`;
    case "failed":
      return `Conversion failed: ${outcome.message}`;
    case "error":
      return `Upload could not be processed: ${outcome.message}`;
  }
}
