"use client";

import { useState } from "react";
import "../public.css";

type Result = { status: string; message: string } | null;

const TONE_FOR_STATUS: Record<string, string> = {
  ok: "hp-alert-ok",
  duplicate: "hp-alert-warning",
  needs_mapping: "hp-alert-warning",
  phi_rejected: "hp-alert-danger",
  failed: "hp-alert-danger",
  error: "hp-alert-danger",
};

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
    <main className="hp-shell">
      <section className="hp-hero">
        <span className="hp-eyebrow">Operator upload</span>
        <h1>Upload a monthly export</h1>
        <p className="hp-lede">Upload your hospital system&apos;s monthly export file.</p>

        <form onSubmit={handleSubmit} className="hp-form-card">
          <div className="hp-field">
            <label htmlFor="file">Export file</label>
            <input id="file" name="file" type="file" accept=".csv" required />
          </div>
          <button type="submit" className="hp-button hp-button-block" disabled={submitting}>
            {submitting ? "Uploading..." : "Upload"}
          </button>
        </form>
      </section>

      {result && (
        <div className="hp-content-narrow">
          <p
            className={`hp-alert ${TONE_FOR_STATUS[result.status] ?? "hp-alert-danger"}`}
            role={result.status === "ok" ? "status" : "alert"}
          >
            {result.message}
          </p>
        </div>
      )}
    </main>
  );
}
