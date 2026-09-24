type EmptyStateProps = {
  title: string;
  message: string;
};

export function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <main className="dc-dashboard">
      <div className="dc-state-card">
        <h1>{title}</h1>
        <p className="dc-muted">{message}</p>
      </div>
    </main>
  );
}
