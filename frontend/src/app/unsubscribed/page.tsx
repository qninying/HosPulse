import Link from "next/link";
import "../public.css";

type PageProps = {
  searchParams: Promise<{ ok?: string }>;
};

export default async function UnsubscribedPage({ searchParams }: PageProps) {
  const { ok } = await searchParams;
  const succeeded = ok === "1";

  return (
    <main className="hp-shell">
      <div className="hp-content-narrow">
        <h1>{succeeded ? "You're unsubscribed" : "That link didn't work"}</h1>
        {succeeded ? (
          <p className="hp-alert hp-alert-ok" role="status">
            You won&apos;t receive any more weekly briefing emails at this address.
          </p>
        ) : (
          <p className="hp-alert hp-alert-danger" role="alert">
            This unsubscribe link is invalid or has expired. If you keep receiving emails
            you don&apos;t want, reply to the briefing email directly and we&apos;ll remove you by hand.
          </p>
        )}
        <p style={{ marginTop: 16 }}>
          <Link href="/" className="hp-back-link">
            &larr; Back to HosPulse
          </Link>
        </p>
      </div>
    </main>
  );
}
