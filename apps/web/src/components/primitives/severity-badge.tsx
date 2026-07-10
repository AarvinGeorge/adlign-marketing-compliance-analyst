// meta: SeverityBadge primitive. High = danger tint, Medium = warning tint,
// Low = muted gray, per DESIGN.md semantic colors and the prototype's rule
// rows. Read-only in MVP1 (severity editing belongs to the deferred U4).

import type { Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

const tone: Record<Severity, string> = {
  High: "bg-danger-bg text-danger-text",
  Medium: "bg-warning-bg text-warning-text",
  Low: "bg-muted text-muted-foreground",
};

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center rounded-pill px-2 text-[11px] font-semibold",
        tone[severity],
        className
      )}
    >
      {severity}
    </span>
  );
}
