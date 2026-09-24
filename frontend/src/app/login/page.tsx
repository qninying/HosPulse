import { sendMagicLink } from "./actions";

type PageProps = {
  searchParams: Promise<{ sent?: string; error?: string }>;
};

export default async function LoginPage({ searchParams }: PageProps) {
  const { sent, error } = await searchParams;

  return (
    <main>
      <h1>Sign in to HosPulse</h1>
      <p>Enter your email and we&apos;ll send you a one-time sign-in link.</p>

      <form action={sendMagicLink}>
        <label htmlFor="email">Email</label>{" "}
        <input id="email" name="email" type="email" required placeholder="you@example.com" />{" "}
        <button type="submit">Send sign-in link</button>
      </form>

      {sent && (
        <p role="status">Check your email for a sign-in link. It expires shortly, so use it soon.</p>
      )}
      {error && <p role="alert">We couldn&apos;t send that link. ({error})</p>}
    </main>
  );
}
