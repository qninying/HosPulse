// Next.js's automatic route-level Suspense fallback -- static skeleton
// markup, no client JS, no spinner component.
export default function DashboardLoading() {
  return (
    <main className="dc-dashboard">
      <div className="dc-skeleton dc-skeleton-title" />
      <section className="dc-kpi-row">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="dc-skeleton dc-skeleton-kpi" />
        ))}
      </section>
      <section className="dc-grid-2">
        <div className="dc-skeleton dc-skeleton-panel" />
        <div className="dc-skeleton dc-skeleton-panel" />
      </section>
    </main>
  );
}
