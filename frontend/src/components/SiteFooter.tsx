import Link from "next/link";

const CONTACT_EMAIL = "qninying@quinaillc.com";

// Compliance follow-up item 5: business details and legal links, present
// on every page via layout.tsx -- there was previously no way to find
// who operates HosPulse or how to contact them anywhere on the site.
export function SiteFooter() {
  return (
    <footer className="site-footer">
      <p>
        HosPulse is operated by Quinai LLC &middot;{" "}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
      </p>
      <nav className="site-footer-nav">
        <Link href="/privacy">Privacy Policy</Link>
        <Link href="/terms">Terms of Service</Link>
      </nav>
    </footer>
  );
}
