type CriterionDetailProps = {
  name: string;
  status: string;
  values: Record<string, unknown>;
};

const CRITERION_TONE: Record<string, string> = {
  triggered: "dc-pill-critical",
  not_triggered: "dc-pill-ok",
  not_assessable: "dc-pill-no_data",
};

function titleCase(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "not available";
  if (Array.isArray(value)) return value.map(formatValue).join(", ");
  return String(value);
}

// Renders early_warning.py's CriterionResult.to_json() output (an exact
// snapshot of the real numbers that produced this criterion's status --
// REQ-005's trust requirement) as a readable list rather than a raw JSON
// dump. Field names vary per criterion (see the three _evaluate_* functions
// in early_warning.py), so this stays generic instead of hardcoding them.
export function CriterionDetail({ name, status, values }: CriterionDetailProps) {
  const entries = Object.entries(values);
  return (
    <div className="dc-criterion">
      <div className="dc-criterion-head">
        <span className="dc-criterion-name">{titleCase(name)}</span>
        <span className={`dc-pill ${CRITERION_TONE[status] ?? "dc-pill-no_data"}`}>
          {titleCase(status)}
        </span>
      </div>
      {entries.length > 0 && (
        <dl className="dc-criterion-values">
          {entries.map(([key, value]) => (
            <div key={key} className="dc-criterion-row">
              <dt>{titleCase(key)}</dt>
              <dd>{formatValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
