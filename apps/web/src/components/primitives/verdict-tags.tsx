// meta: VerdictTags primitive (v2.2 delta, Delta 2; canonical over the
// prototype's flag-type badges). Three compact pills on one line: axis A
// Compliant/Non-compliant, axis B Matches approval/Differs from approval/N/A
// (gray when null, i.e. no library entry applies), and the visually dominant
// named intersection. Reads a CheckResult from the frozen types.ts contract.

import type { CheckResult, IntersectionTag } from "@/lib/types";
import { cn } from "@/lib/utils";

const TAG_LABEL: Record<IntersectionTag, string> = {
  all_good: "All good",
  drifted_but_compliant: "Drifted but compliant",
  approved_but_non_compliant: "Approved but non-compliant",
  unapproved_violation: "Unapproved violation",
};

const TAG_TONE: Record<IntersectionTag, string> = {
  all_good: "bg-success-bg text-success-text border-success/30",
  drifted_but_compliant: "bg-warning-bg text-warning-text border-warning/30",
  approved_but_non_compliant: "bg-danger-bg text-danger-text border-danger/30",
  unapproved_violation: "bg-danger-bg text-danger-text border-danger/30",
};

function Pill({
  children,
  className,
  dominant = false,
}: {
  children: React.ReactNode;
  className?: string;
  dominant?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center whitespace-nowrap rounded-pill border px-2 text-[11px]",
        dominant ? "font-semibold" : "font-medium",
        className
      )}
    >
      {children}
    </span>
  );
}

export function VerdictTags({
  verdicts,
  className,
}: {
  verdicts: CheckResult;
  className?: string;
}) {
  const { axis_a, axis_b, intersection_tag } = verdicts;
  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
      <Pill
        className={
          axis_a
            ? "border-transparent bg-success-bg text-success-text"
            : "border-transparent bg-danger-bg text-danger-text"
        }
      >
        {axis_a ? "Compliant" : "Non-compliant"}
      </Pill>
      <Pill
        className={
          axis_b === null
            ? "border-transparent bg-muted text-muted-foreground"
            : axis_b
              ? "border-transparent bg-success-bg text-success-text"
              : "border-transparent bg-warning-bg text-warning-text"
        }
      >
        {axis_b === null
          ? "N/A"
          : axis_b
            ? "Matches approval"
            : "Differs from approval"}
      </Pill>
      <Pill dominant className={TAG_TONE[intersection_tag]}>
        {TAG_LABEL[intersection_tag]}
      </Pill>
    </div>
  );
}

export function IntersectionPill({
  tag,
  className,
}: {
  tag: IntersectionTag;
  className?: string;
}) {
  return (
    <Pill dominant className={cn(TAG_TONE[tag], className)}>
      {TAG_LABEL[tag]}
    </Pill>
  );
}
