import { describe, expect, it } from "vitest";

import { parseUnsubscribeOutput } from "./unsubscribeOutcome";

describe("parseUnsubscribeOutput", () => {
  it("recognizes a successful unsubscribe", () => {
    expect(parseUnsubscribeOutput('{"status": "unsubscribed"}')).toEqual({
      status: "unsubscribed",
    });
  });

  it("recognizes an invalid token", () => {
    expect(parseUnsubscribeOutput('{"status": "invalid_token"}')).toEqual({
      status: "invalid_token",
    });
  });

  it("takes the last line when the script printed more than one", () => {
    const stdout = '{"status": "invalid_token"}\n{"status": "unsubscribed"}';
    expect(parseUnsubscribeOutput(stdout)).toEqual({ status: "unsubscribed" });
  });

  it("reports an error, not a crash, on empty output", () => {
    const result = parseUnsubscribeOutput("");
    expect(result.status).toBe("error");
  });

  it("reports an error, not a crash, on unparseable output", () => {
    const result = parseUnsubscribeOutput("not json at all");
    expect(result.status).toBe("error");
  });

  it("passes through a server-reported error message", () => {
    const result = parseUnsubscribeOutput('{"status": "error", "message": "server misconfigured"}');
    expect(result).toEqual({ status: "error", message: "server misconfigured" });
  });
});
