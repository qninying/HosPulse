import Link from "next/link";
import type { LatestBriefing } from "@/lib/companyBriefing";

type AttentionPanelProps = {
  briefing: LatestBriefing;
  hospitalNames: Record<string, string | null>;
};

// Renders the real briefings.body verbatim as one narrative block -- not
// reformatted into per-sentence citations, since the stored text doesn't
// structurally guarantee that shape. Real drill-in comes from the hospital
// chips below it, built from the briefing's own provider_ccns.
export function AttentionPanel({ briefing, hospitalNames }: AttentionPanelProps) {
  return (
    <div>
      <p className="dc-muted dc-small">
        AI-written &middot; as of {new Date(briefing.asOfDate).toLocaleDateString("en-US", { dateStyle: "medium" })}
      </p>
      <p className="dc-brief-body">{briefing.body}</p>
      {briefing.providerCcns.length > 0 && (
        <div className="dc-chip-row">
          {briefing.providerCcns.map((ccn) => (
            <Link key={ccn} href={`/dashboard/${ccn}`} className="dc-chip">
              {hospitalNames[ccn] ?? ccn}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
