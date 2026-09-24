type ErrorStateProps = {
  message: string;
};

export function ErrorState({ message }: ErrorStateProps) {
  return (
    <main>
      <h1>Data retrieval error</h1>
      <p role="alert">{message}</p>
    </main>
  );
}
