import Link from "next/link";
import "./public.css";
import {
  normalizeSearchTerm,
  searchHospitalsByName,
} from "@/lib/hospitalSearch";

type PageProps = {
  searchParams: Promise<{ q?: string }>;
};

// STORY-003 step 2: public search by hospital name, with a not-found
// message and a data-retrieval-error message. Trend display (three years,
// data year, lag disclosure) lands in the next step, once a specific
// hospital is chosen from these results.
export default async function Home({ searchParams }: PageProps) {
  const { q } = await searchParams;
  const term = normalizeSearchTerm(q);

  const outcome = term ? await searchHospitalsByName(term) : null;

  return (
    <main className="hp-shell">
      <section className="hp-hero">
        <span className="hp-eyebrow">Public CMS cost report data &middot; no login required</span>
        <h1>HosPulse Health Snapshot</h1>
        <p className="hp-lede">
          Search for a rural or Critical Access Hospital to see its public
          financial trends.
        </p>

        <form action="/" method="GET" className="hp-form-card">
          <label htmlFor="q">Hospital name</label>
          <div className="hp-search-row">
            <input
              id="q"
              name="q"
              type="text"
              defaultValue={term}
              placeholder="e.g. Anson General"
            />
            <button type="submit" className="hp-button">Search</button>
          </div>
        </form>
      </section>

      <div className="hp-content">
        {outcome && !outcome.ok && (
          <p className="hp-alert hp-alert-danger" role="alert">
            We couldn&apos;t retrieve hospital data right now. Please try
            again in a moment. ({outcome.error})
          </p>
        )}

        {outcome && outcome.ok && outcome.hospitals.length === 0 && (
          <p className="hp-empty">
            No hospital found matching &quot;{term}&quot;.
          </p>
        )}

        {outcome && outcome.ok && outcome.hospitals.length > 0 && (
          <>
            <p className="hp-result-count">
              {outcome.hospitals.length}{" "}
              {outcome.hospitals.length === 1 ? "match" : "matches"}
            </p>
            <ul className="hp-result-list">
              {outcome.hospitals.map((h) => (
                <li key={h.provider_ccn}>
                  <Link
                    href={`/hospital/${h.provider_ccn}`}
                    className="hp-result-card"
                  >
                    <span>{h.name ?? "(name not yet resolved)"}</span>
                    <span className="hp-state-badge">{h.state}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </main>
  );
}
