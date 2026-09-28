import Link from "next/link";
import "../public.css";

const LAST_UPDATED = "September 28, 2026";
const CONTACT_EMAIL = "qninying@quinaillc.com";

export default function PrivacyPage() {
  return (
    <main className="hp-shell">
      <div className="hp-content-narrow">
        <p>
          <Link href="/" className="hp-back-link">
            &larr; Back to HosPulse
          </Link>
        </p>
        <h1>Privacy Policy</h1>
        <p>Last updated: {LAST_UPDATED}</p>

        <p>
          HosPulse is operated by Quinai LLC (&quot;HosPulse,&quot; &quot;we,&quot; &quot;us&quot;).
          This page describes, plainly and accurately, what data HosPulse actually collects
          today and what happens to it. It is not a boilerplate template &mdash; it is written
          to match the product as it currently exists.
        </p>

        <h2>The public Health Snapshot</h2>
        <p>
          Anyone can search and view a hospital&apos;s public financial trend data with no
          account, no sign-up, and no personal information collected. This data comes from
          public CMS cost report filings, not from you.
        </p>

        <h2>What we collect if you create an account</h2>
        <p>
          Hospital management company staff sign in with a one-time email link. We collect
          your email address to create and authenticate your account, and to know which
          management company you belong to. We do not collect a password, and we do not
          collect your name, phone number, or physical address unless you send it to us
          directly (for example, by emailing us).
        </p>

        <h2>Files you upload</h2>
        <p>
          If you upload a monthly cost report export, HosPulse automatically scans it before
          storing or logging anything. Any file that appears to contain patient names, birth
          dates, or medical record numbers is rejected outright &mdash; it is never stored,
          and the rejection log never contains the sensitive value itself, only which column
          triggered it. HosPulse is not built to receive patient health information, and this
          check exists specifically to catch a file uploaded to the wrong place.
        </p>
        <p>
          Financial figures from an accepted file (cash balances, receivables, and similar
          business metrics) are stored and used to compute the trends and findings your
          company sees on its own dashboard.
        </p>

        <h2>Who else can see your company&apos;s data</h2>
        <p>
          Only your own company&apos;s staff. HosPulse enforces this with database-level
          row-level security, not just application logic &mdash; a staff member at one
          management company cannot see another company&apos;s uploaded data or findings,
          even if they tried to query for it directly.
        </p>

        <h2>The weekly email briefing</h2>
        <p>
          If your company has hospitals assigned to it, HosPulse emails a weekly briefing to
          your registered address. Every briefing email contains a working, one-click
          unsubscribe link. Clicking it stops future briefings to that address; it does not
          delete your account or your company&apos;s other data.
        </p>

        <h2>Cookies</h2>
        <p>
          HosPulse uses one cookie: a session cookie that keeps you signed in. It is strictly
          necessary for the dashboard to function and is not used for advertising, tracking,
          or analytics. HosPulse does not load any third-party analytics, advertising, or
          tracking scripts.
        </p>

        <h2>Who we share data with</h2>
        <p>
          HosPulse uses a small number of service providers to operate: Supabase (database,
          authentication, and file storage), Anthropic&apos;s Claude API (to generate
          briefings and findings from your company&apos;s already-computed metrics, never
          from raw uploaded files), and Resend (to deliver the weekly briefing email). These
          providers process data on our behalf to run the service; HosPulse does not sell
          your data or share it with anyone else.
        </p>

        <h2>How long we keep data</h2>
        <p>
          We keep your account and your company&apos;s data for as long as your account is
          active. If you want your data deleted sooner, see below.
        </p>

        <h2>Requesting deletion</h2>
        <p>
          To request deletion of your account or your company&apos;s data, email{" "}
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. HosPulse does not yet have
          an automated self-service deletion tool &mdash; this request is handled by a
          person, not a script.
        </p>

        <h2>Children</h2>
        <p>
          HosPulse is a business tool for hospital management company staff. It is not
          directed at, and does not knowingly collect information from, anyone under 18.
        </p>

        <h2>Changes to this policy</h2>
        <p>
          If what HosPulse actually collects or does with data changes, this page will be
          updated to match, and the &quot;last updated&quot; date above will change with it.
        </p>

        <h2>Contact</h2>
        <p>
          Quinai LLC
          <br />
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
        </p>
      </div>
    </main>
  );
}
