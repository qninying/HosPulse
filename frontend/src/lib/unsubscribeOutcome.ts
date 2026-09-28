// Mirrors the exportUpload.ts split: this file holds only the pure piece
// of the bridge to pipeline/unsubscribe.py -- parsing its final JSON
// stdout line into a typed outcome -- so it's unit-testable without
// spawning a real process. The route handler (app/api/unsubscribe/route.ts)
// does the actual spawning and is verified live instead.

export type UnsubscribeOutcome =
  | { status: "unsubscribed" }
  | { status: "invalid_token" }
  | { status: "error"; message: string };

export function parseUnsubscribeOutput(stdout: string): UnsubscribeOutcome {
  const lines = stdout.split("\n").map((l) => l.trim()).filter(Boolean);
  const lastLine = lines[lines.length - 1];
  if (!lastLine) {
    return { status: "error", message: "no output from unsubscribe script" };
  }

  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(lastLine);
  } catch {
    return { status: "error", message: `unparseable unsubscribe output: ${lastLine}` };
  }

  if (parsed.status === "unsubscribed") return { status: "unsubscribed" };
  if (parsed.status === "invalid_token") return { status: "invalid_token" };
  return {
    status: "error",
    message: typeof parsed.message === "string" ? parsed.message : "unsubscribe failed",
  };
}
