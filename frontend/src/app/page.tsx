import Link from "next/link";
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
    <main>
      <h1>HosPulse Health Snapshot</h1>
      <p>Search for a hospital to see its public financial trends.</p>

      <form action="/" method="GET">
        <label htmlFor="q">Hospital name</label>{" "}
        <input
          id="q"
          name="q"
          type="text"
          defaultValue={term}
          placeholder="e.g. Anson General"
        />{" "}
        <button type="submit">Search</button>
      </form>

      {outcome && !outcome.ok && (
        <p role="alert">
          We couldn&apos;t retrieve hospital data right now. Please try again
          in a moment. ({outcome.error})
        </p>
      )}

      {outcome && outcome.ok && outcome.hospitals.length === 0 && (
        <p>No hospital found matching &quot;{term}&quot;.</p>
      )}

      {outcome && outcome.ok && outcome.hospitals.length > 0 && (
        <ul>
          {outcome.hospitals.map((h) => (
            <li key={h.provider_ccn}>
              <Link href={`/hospital/${h.provider_ccn}`}>
                {h.name ?? "(name not yet resolved)"}
              </Link>{" "}
              — {h.state}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
