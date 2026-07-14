// meta: FlagSeverityControl (per-flag severity increment, 2026-07-14).
// Dropdown-editable severity badge on flag rows and the flag detail panel:
// ordinal-ramp dot (High #991b1b, Medium #dc2626, Low #f47c7c; darker =
// worse, never color alone) + ink text label showing EFFECTIVE severity
// (human override ?? rule recommendation). Picking a value PATCHes
// /flags/{id}/severity; when overridden, a subtle asterisk marks the edit
// (native tooltip "Adjusted by you · recommended High") and the dropdown
// gains "Reset to recommended", which PATCHes null. Reuses the scorecard
// studio's dropdown-editable badge pattern.

"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { useFlagSeverity } from "@/lib/data";
import type { Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

const RAMP: Record<Severity, string> = {
  High: "#991b1b",
  Medium: "#dc2626",
  Low: "#f47c7c",
};

const RESET = "__reset__";

export function FlagSeverityControl({
  flagId,
  productId,
  effective,
  recommended,
  overridden,
  className,
}: {
  flagId: string;
  productId: string;
  effective: Severity;
  recommended: Severity;
  overridden: boolean;
  className?: string;
}) {
  const severity = useFlagSeverity(productId);

  return (
    <Select
      value={effective}
      onValueChange={(v) => {
        if (v === RESET) {
          severity.mutate({ flagId, severity: null });
        } else if (v !== effective) {
          severity.mutate({ flagId, severity: v as Severity });
        }
      }}
      disabled={severity.isPending}
    >
      <SelectTrigger
        size="sm"
        aria-label={`Severity for flag ${flagId}`}
        title={
          overridden
            ? `Adjusted by you · recommended ${recommended}`
            : undefined
        }
        className={cn(
          "h-[22px] w-auto gap-1 rounded-pill border-border bg-background px-2 py-0 text-[11px] font-semibold shadow-none",
          className
        )}
      >
        <span
          className="size-2 flex-none rounded-pill"
          style={{ backgroundColor: RAMP[effective] }}
          aria-hidden="true"
        />
        {effective}
        {overridden ? (
          <span className="text-muted-foreground" aria-label="Adjusted by you">
            *
          </span>
        ) : null}
      </SelectTrigger>
      {/* position="popper" (floating-ui, viewport-relative): the wrapper's
          "item-aligned" default positions the menu at document coordinates in
          this scrolled layout, rendering it thousands of px off-screen, so
          mouse users saw nothing open (2026-07-13 fix). */}
      <SelectContent position="popper" align="start" sideOffset={4}>
        {(Object.keys(RAMP) as Severity[]).map((s) => (
          <SelectItem key={s} value={s} className="text-xs">
            <span
              className="size-2 flex-none rounded-pill"
              style={{ backgroundColor: RAMP[s] }}
              aria-hidden="true"
            />
            {s}
            {s === recommended ? (
              <span className="text-muted-foreground"> (recommended)</span>
            ) : null}
          </SelectItem>
        ))}
        {overridden ? (
          <SelectItem value={RESET} className="text-xs text-muted-foreground">
            Reset to recommended
          </SelectItem>
        ) : null}
      </SelectContent>
    </Select>
  );
}
