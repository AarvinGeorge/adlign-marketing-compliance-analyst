// meta: LifecycleChip primitive (v2.2 delta, Delta 3). Current state only:
// Open (danger), Confirmed (accent), Assigned · team (accent), Fix pending
// verification (warning + clock), Closed (success + check), Dismissed (muted;
// the ROW carries the strikethrough). LifecycleStrip renders the full
// horizontal sequence for flag detail with the current state highlighted.

import { Check, Clock } from "lucide-react";
import type { FlagState } from "@/lib/types";
import { cn } from "@/lib/utils";

export function lifecycleLabel(state: FlagState, team?: string | null): string {
  switch (state) {
    case "open":
      return "Open";
    case "confirmed":
      return "Confirmed";
    case "assigned":
      return team ? `Assigned · ${team}` : "Assigned";
    case "fix_pending_verification":
      return "Fix pending verification";
    case "closed":
      return "Closed";
    case "dismissed":
      return "Dismissed";
  }
}

export function LifecycleChip({
  state,
  team,
  className,
}: {
  state: FlagState;
  team?: string | null;
  className?: string;
}) {
  const label = lifecycleLabel(state, team);
  const tone: Record<FlagState, string> = {
    open: "bg-danger-bg text-danger-text",
    confirmed: "bg-accent text-accent-foreground",
    assigned: "bg-accent text-accent-foreground",
    fix_pending_verification: "bg-warning-bg text-warning-text",
    closed: "bg-success-bg text-success-text",
    dismissed: "bg-muted text-muted-foreground",
  };
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center gap-1 whitespace-nowrap rounded-pill px-2 text-[11px] font-medium",
        tone[state],
        state === "dismissed" && "line-through decoration-muted-foreground/60",
        className
      )}
    >
      {state === "fix_pending_verification" ? <Clock className="size-3" /> : null}
      {state === "closed" ? <Check className="size-3" /> : null}
      {label}
    </span>
  );
}

const SEQUENCE: FlagState[] = [
  "open",
  "confirmed",
  "assigned",
  "fix_pending_verification",
  "closed",
];

export function LifecycleStrip({
  state,
  team,
  className,
}: {
  state: FlagState;
  team?: string | null;
  className?: string;
}) {
  if (state === "dismissed") {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <LifecycleChip state="dismissed" />
        <span className="text-xs text-muted-foreground">
          terminal state, kept for audit
        </span>
      </div>
    );
  }
  const currentIdx = SEQUENCE.indexOf(state);
  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
      {SEQUENCE.map((s, i) => (
        <span key={s} className="flex items-center gap-1.5">
          {i > 0 ? (
            <span className="h-px w-3 bg-border" aria-hidden="true" />
          ) : null}
          {i === currentIdx ? (
            <LifecycleChip state={s} team={team} />
          ) : (
            <span
              className={cn(
                "inline-flex h-[22px] items-center gap-1 whitespace-nowrap rounded-pill px-2 text-[11px] font-medium",
                i < currentIdx
                  ? "text-muted-foreground"
                  : "text-muted-foreground/50"
              )}
            >
              {i < currentIdx ? <Check className="size-3" /> : null}
              {lifecycleLabel(s, s === "assigned" ? team : undefined)}
            </span>
          )}
        </span>
      ))}
    </div>
  );
}
