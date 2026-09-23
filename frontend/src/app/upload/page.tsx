"use client";

import { useState } from "react";

type Result = { status: string; message: string } | null;

// STORY-005: a minimal operator upload page. Posts directly to
// /api/upload as multipart/form-data and shows the real outcome the
// route returns (accepted, duplicate, needs_mapping, rejected) --
// nothing here re-derives or guesses that outcome client-side.
export default function UploadPage() {
  const [result, setResult] = useState<Result>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    setSubmitting(true);
    setResult(null);
    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });
      const body = (await response.json()) as { status: string; message: string };
      setResult(body);
    } catch {
      setResult({ status: "error", message: "Upload request failed to reach the server." });
    } finally {
      setSubmitting(false);
      form.reset();
    }
  }

  return (
    <main>
      <h1>Upload a monthly export</h1>
      <p>Upload your hospital system&apos;s monthly export file.</p>

      <form onSubmit={handleSubmit}>
        <label htmlFor="file">Export file</label>{" "}
        <input id="file" name="file" type="file" accept=".csv" required />{" "}
        <button type="submit" disabled={submitting}>
          {submitting ? "Uploading..." : "Upload"}
        </button>
      </form>

      {result && (
        <p role={result.status === "ok" ? "status" : "alert"}>{result.message}</p>
      )}
    </main>
  );
}
