import type { ReactNode } from "react";

type CardProps = {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

// The one layout primitive every dashboard card composes -- this is what
// keeps card heights, borders, and spacing consistent instead of each card
// hand-rolling its own markup.
export function Card({ title, action, children, className }: CardProps) {
  return (
    <section className={`dc-card${className ? ` ${className}` : ""}`}>
      {(title || action) && (
        <div className="dc-card-head">
          {title && <h3>{title}</h3>}
          {action}
        </div>
      )}
      <div className="dc-card-body">{children}</div>
    </section>
  );
}
