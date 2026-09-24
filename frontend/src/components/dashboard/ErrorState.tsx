type ErrorStateProps = {
  message: string;
};

export function ErrorState({ message }: ErrorStateProps) {
  return (
    <main className="dc-dashboard">
      <div className="dc-state-card dc-state-card-error">
        <h1>Data retrieval error</h1>
        <p role="alert">{message}</p>
      </div>
    </main>
  );
}
