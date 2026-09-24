import "../public.css";
import { sendMagicLink, verifyOtpCode } from "./actions";

type PageProps = {
  searchParams: Promise<{ sent?: string; error?: string; email?: string }>;
};

export default async function LoginPage({ searchParams }: PageProps) {
  const { sent, error, email } = await searchParams;

  return (
    <main className="hp-shell">
      <section className="hp-hero" style={{ paddingBottom: 0 }}>
        <h1 style={{ fontSize: 28 }}>Sign in to HosPulse</h1>
        <p className="hp-lede">Enter your email and we&apos;ll send you a one-time sign-in link.</p>
      </section>

      <div className="hp-content-narrow" style={{ marginTop: 24 }}>
        <div className="hp-form-card">
          <form action={sendMagicLink}>
            <div className="hp-field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                required
                defaultValue={email}
                placeholder="you@example.com"
              />
            </div>
            <button type="submit" className="hp-button hp-button-block">
              Send sign-in link
            </button>
          </form>

          {sent && (
            <p className="hp-alert hp-alert-ok" role="status" style={{ marginTop: 16 }}>
              Check your email for a sign-in link. It expires shortly, so use it soon.
            </p>
          )}
          {error && (
            <p className="hp-alert hp-alert-danger" role="alert" style={{ marginTop: 16 }}>
              That didn&apos;t work. ({error})
            </p>
          )}

          <div className="hp-divider">or use the code instead</div>

          <p className="hp-hint">
            Some email providers (Gmail included) automatically visit links in email to scan them
            for safety, which can use up a one-time sign-in link before you click it yourself. If
            clicking the link doesn&apos;t work, enter the 6-digit code from the same email below.
          </p>

          <form action={verifyOtpCode}>
            <div className="hp-field">
              <label htmlFor="code-email">Email</label>
              <input
                id="code-email"
                name="email"
                type="email"
                required
                defaultValue={email}
                placeholder="you@example.com"
              />
            </div>
            <div className="hp-field">
              <label htmlFor="token">Code</label>
              <input
                id="token"
                name="token"
                type="text"
                inputMode="numeric"
                required
                placeholder="123456"
              />
            </div>
            <button type="submit" className="hp-button hp-button-block">
              Verify code
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
