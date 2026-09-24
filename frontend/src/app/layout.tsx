import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = {
  title: "HosPulse",
  description: "Early-warning intelligence for rural and Critical Access Hospital management companies.",
};

// Runs before paint to avoid a flash of the wrong theme -- same technique
// the Command Center's own pages already use, plain vanilla JS, no client
// component or hydration needed for a one-time synchronous read.
const THEME_INIT_SCRIPT = `(function () {
  try {
    var saved = localStorage.getItem("hospulse-theme");
    if (saved === "light" || saved === "dark") {
      document.documentElement.setAttribute("data-theme", saved);
    }
  } catch (e) {}
})();`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
