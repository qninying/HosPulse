import Link from "next/link";
import { createSupabaseServerClient } from "@/lib/supabaseServerClient";

const SUN_ICON =
  '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const MOON_ICON =
  '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>';

// Same manual toggle as the Command Center: a plain vanilla-JS click
// handler, no client component or hydration needed for something this
// small, matching this codebase's "no unnecessary client JS" convention.
const THEME_TOGGLE_SCRIPT = `(function () {
  var KEY = "hospulse-theme";
  var SUN = ${JSON.stringify(SUN_ICON)};
  var MOON = ${JSON.stringify(MOON_ICON)};
  function currentTheme() {
    var explicit = document.documentElement.getAttribute("data-theme");
    if (explicit === "light" || explicit === "dark") return explicit;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function render() {
    var btn = document.getElementById("theme-toggle");
    if (btn) btn.innerHTML = currentTheme() === "dark" ? MOON : SUN;
  }
  function toggle() {
    var next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
    render();
  }
  render();
  var btn = document.getElementById("theme-toggle");
  if (btn) btn.addEventListener("click", toggle);
})();`;

export async function SiteHeader() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <header className="site-header">
      <Link href="/" className="site-brand">
        <img src="/logo-dark.svg" alt="HosPulse" height={24} />
      </Link>
      <nav className="site-nav">
        <Link href="/">Health Snapshot</Link>
        <Link href="/upload">Upload</Link>
        <Link href="/dashboard">Dashboard</Link>
      </nav>
      <div className="site-user">
        {user ? (
          <form action="/logout" method="POST">
            <span>{user.email}</span> <button type="submit">Sign out</button>
          </form>
        ) : (
          <Link href="/login">Sign in</Link>
        )}
        <button
          id="theme-toggle"
          className="theme-toggle"
          type="button"
          aria-label="Switch between day and night theme"
          title="Day / Night"
        />
        <script dangerouslySetInnerHTML={{ __html: THEME_TOGGLE_SCRIPT }} />
      </div>
    </header>
  );
}
