import { sendMagicLink, verifyOtpCode } from "./actions";

type PageProps = {
  searchParams: Promise<{ sent?: string; error?: string; email?: string }>;
};

export default async function LoginPage({ searchParams }: PageProps) {
  const { sent, error, email } = await searchParams;

  return (
    <main>
      <h1>Sign in to HosPulse</h1>
      <p>Enter your email and we&apos;ll send you a one-time sign-in link.</p>

      <form action={sendMagicLink}>
        <label htmlFor="email">Email</label>{" "}
        <input id="email" name="email" type="email" required defaultValue={email} placeholder="you@example.com" />{" "}
        <button type="submit">Send sign-in link</button>
      </form>

      {sent && (
        <p role="status">Check your email for a sign-in link. It expires shortly, so use it soon.</p>
      )}
      {error && <p role="alert">That didn&apos;t work. ({error})</p>}

      <p>
        <strong>If clicking the link doesn&apos;t work</strong>, some email providers (Gmail
        included) automatically visit links in email to scan them for safety, which can use up a
        one-time sign-in link before you click it yourself. Enter the 6-digit code from the same
        email instead:
      </p>

      <form action={verifyOtpCode}>
        <label htmlFor="code-email">Email</label>{" "}
        <input id="code-email" name="email" type="email" required defaultValue={email} placeholder="you@example.com" />{" "}
        <label htmlFor="token">Code</label>{" "}
        <input id="token" name="token" type="text" inputMode="numeric" required placeholder="123456" />{" "}
        <button type="submit">Verify code</button>
      </form>
    </main>
  );
}
