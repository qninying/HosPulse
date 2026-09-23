import { describe, expect, it } from "vitest";

import {
  httpStatusFor,
  messageFor,
  parseNormalizerOutput,
} from "./exportUpload";

describe("parseNormalizerOutput", () => {
  it("parses a fresh ok result", () => {
    const stdout = JSON.stringify({
      status: "ok",
      is_duplicate: false,
      source_system: "epic",
      metrics_count: 4,
      error_message: null,
    });
    const outcome = parseNormalizerOutput(stdout, 0);
    expect(outcome).toEqual({ status: "ok", sourceSystem: "epic", metricsCount: 4 });
  });

  it("parses a duplicate result even though status is still ok", () => {
    // export_normalizer.py's idempotency short-circuit returns the
    // original outcome's status (e.g. "ok") plus is_duplicate=true --
    // duplicate must take priority over the underlying status.
    const stdout = JSON.stringify({
      status: "ok",
      is_duplicate: true,
      source_system: "epic",
      metrics_count: 0,
      error_message: null,
    });
    const outcome = parseNormalizerOutput(stdout, 0);
    expect(outcome).toEqual({ status: "duplicate", sourceSystem: "epic" });
  });

  it("parses needs_mapping", () => {
    const stdout = JSON.stringify({
      status: "needs_mapping",
      is_duplicate: false,
      source_system: null,
      metrics_count: 0,
      error_message: null,
    });
    expect(parseNormalizerOutput(stdout, 0)).toEqual({ status: "needs_mapping" });
  });

  it("parses a phi_rejected result", () => {
    const stdout = JSON.stringify({
      status: "phi_rejected",
      message: "1 PHI field(s) detected: 'Patient Name' (patient_name)",
    });
    expect(parseNormalizerOutput(stdout, 1)).toEqual({
      status: "phi_rejected",
      message: "1 PHI field(s) detected: 'Patient Name' (patient_name)",
    });
  });

  it("parses a failed conversion", () => {
    const stdout = JSON.stringify({
      status: "failed",
      is_duplicate: false,
      source_system: "epic",
      metrics_count: 0,
      error_message: "ValueError: unrecognized month format: 'not-a-date'",
    });
    expect(parseNormalizerOutput(stdout, 1)).toEqual({
      status: "failed",
      message: "ValueError: unrecognized month format: 'not-a-date'",
    });
  });

  // The real bug this test locks in: the PHI gate logs a structured
  // audit line to stdout via print() before the CLI's own result line,
  // so stdout is not guaranteed to be a single line -- found live while
  // building this bridge.
  it("uses the last line when the PHI audit log line precedes the result", () => {
    const auditLine = JSON.stringify({
      timestamp: "2026-09-23T02:30:58Z",
      level: "info",
      service: "export-normalizer",
      event: "phi_scan",
      outcome: "accepted",
      context: { source_file: "epic.csv", categories: [], reason: "clean" },
    });
    const resultLine = JSON.stringify({
      status: "ok",
      is_duplicate: false,
      source_system: "epic",
      metrics_count: 4,
      error_message: null,
    });
    const stdout = `${auditLine}\n${resultLine}\n`;
    expect(parseNormalizerOutput(stdout, 0)).toEqual({
      status: "ok",
      sourceSystem: "epic",
      metricsCount: 4,
    });
  });

  it("returns an error outcome for empty stdout", () => {
    const outcome = parseNormalizerOutput("", 1);
    expect(outcome.status).toBe("error");
  });

  it("returns an error outcome for unparseable stdout", () => {
    const outcome = parseNormalizerOutput("not json at all", 1);
    expect(outcome.status).toBe("error");
  });

  it("returns an error outcome for a well-formed but unrecognized status", () => {
    const stdout = JSON.stringify({ status: "something_new" });
    const outcome = parseNormalizerOutput(stdout, 0);
    expect(outcome.status).toBe("error");
  });
});

describe("httpStatusFor", () => {
  it("maps each outcome to the right HTTP status", () => {
    expect(httpStatusFor({ status: "ok", sourceSystem: "epic", metricsCount: 4 })).toBe(200);
    expect(httpStatusFor({ status: "duplicate", sourceSystem: "epic" })).toBe(409);
    expect(httpStatusFor({ status: "needs_mapping" })).toBe(422);
    expect(httpStatusFor({ status: "phi_rejected", message: "x" })).toBe(422);
    expect(httpStatusFor({ status: "failed", message: "x" })).toBe(422);
    expect(httpStatusFor({ status: "error", message: "x" })).toBe(500);
  });
});

describe("messageFor", () => {
  it("never leaks the PHI reason as if it were a normal message prefix", () => {
    const outcome = messageFor({ status: "phi_rejected", message: "1 PHI field(s) detected" });
    expect(outcome).toContain("Rejected");
  });

  it("names the duplicate outcome explicitly", () => {
    expect(messageFor({ status: "duplicate", sourceSystem: "epic" })).toContain("duplicate");
  });
});
