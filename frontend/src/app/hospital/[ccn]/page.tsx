import Link from "next/link";
import {
  DATA_LAG_NOTE,
  formatMetric,
  getHospitalTrends,
} from "@/lib/hospitalDetail";

type PageProps = {
  params: Promise<{ ccn: string }>;
};

export default async function HospitalPage({ params }: PageProps) {
  const { ccn } = await params;
  const outcome = await getHospitalTrends(ccn);

  if (!outcome.ok && outcome.kind === "not_found") {
    return (
      <main>
        <p>
          <Link href="/">← Back to search</Link>
        </p>
        <h1>Hospital not found</h1>
        <p>No hospital matches &quot;{ccn}&quot;.</p>
      </main>
    );
  }

  if (!outcome.ok) {
    return (
      <main>
        <p>
          <Link href="/">← Back to search</Link>
        </p>
        <h1>Data retrieval error</h1>
        <p role="alert">
          We couldn&apos;t retrieve this hospital&apos;s data right now. ({outcome.error})
        </p>
      </main>
    );
  }

  const { hospital } = outcome;

  return (
    <main>
      <p>
        <Link href="/">← Back to search</Link>
      </p>
      <h1>
        {hospital.name ?? "(name not yet resolved)"} — {hospital.state}
      </h1>
      <p>
        <em>{DATA_LAG_NOTE}</em>
      </p>

      {hospital.years.length === 0 ? (
        <p>No cost report data is available yet for this hospital.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Fiscal year</th>
              <th>Operating margin</th>
              <th>Days cash on hand</th>
              <th>Days in accounts receivable</th>
            </tr>
          </thead>
          <tbody>
            {hospital.years.map((y) => (
              <tr key={y.fiscal_year}>
                <td>{y.fiscal_year}</td>
                <td>{formatMetric(y.operating_margin_pct, "%")}</td>
                <td>{formatMetric(y.days_cash_on_hand, " days")}</td>
                <td>{formatMetric(y.days_in_ar, " days")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {hospital.years.length > 0 && hospital.years.length < 3 && (
        <p>
          Only {hospital.years.length} year
          {hospital.years.length === 1 ? "" : "s"} of data{" "}
          {hospital.years.length === 1 ? "is" : "are"} available for this
          hospital in the public CMS filings — a real reporting gap, not an
          error.
        </p>
      )}
    </main>
  );
}
