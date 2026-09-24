type EmptyStateProps = {
  title: string;
  message: string;
};

export function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <main>
      <h1>{title}</h1>
      <p>{message}</p>
    </main>
  );
}
