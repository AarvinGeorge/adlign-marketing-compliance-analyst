// meta: PropertyChip primitive. Platform icon (lucide) + label + optional
// remove X, per DESIGN.md. Used by U3's detected chips (removable) and, in
// icon-only form via PropertyIcon, by flag rows and coverage chips.
// Note: lucide-react v1 removed brand icons, so Instagram renders as Camera
// and Facebook as ThumbsUp (nearest neutral glyphs; labels disambiguate).

import { Camera, Globe, ThumbsUp, X } from "lucide-react";
import type { PropertyKind } from "@/lib/types";
import { cn } from "@/lib/utils";

export function PropertyIcon({
  kind,
  className,
}: {
  kind: PropertyKind;
  className?: string;
}) {
  const cls = cn("size-3.5", className);
  switch (kind) {
    case "website":
      return <Globe className={cls} aria-label="Website" />;
    case "instagram":
      return <Camera className={cls} aria-label="Instagram" />;
    case "facebook":
      return <ThumbsUp className={cls} aria-label="Facebook" />;
  }
}

export function PropertyChip({
  kind,
  label,
  onRemove,
  className,
}: {
  kind: PropertyKind;
  label: string;
  onRemove?: () => void;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-surface pl-2.5 text-xs font-medium",
        onRemove ? "pr-1" : "pr-2.5",
        className
      )}
    >
      <PropertyIcon kind={kind} className="text-muted-foreground" />
      {label}
      {onRemove ? (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove ${label}`}
          className="flex size-5 items-center justify-center rounded-sm text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="size-3" />
        </button>
      ) : null}
    </span>
  );
}
