// meta: U6 product detail (/products/[id]). API-backed via useProductView:
// metric row computed from live scores + lifecycle overlay, flags list with
// THREE groupings toggleable (by issue / by cluster / by property). Grouping
// is a VIEW, not a decision (Gmail-threading pattern): AI issue groupings
// render with the rationale always visible and a single reversible Ungroup
// action with in-place Undo (PATCH /clusters/{id}/issue-state, rejected then
// suggested); no accept flow. A self-healing auto-trigger fires
// POST /runs/{id}/issue-suggestions once for completed runs with wording
// clusters but zero issue rows. Cluster bulk actions (sequential dispositions
// against POST /flags/{id}/disposition), per-flag disposition via FlagRow,
// lifecycle chips, three-tag verdicts. Demo products (404 from the API) fall
// back to their fixture summaries with no flags.

"use client";

import { use, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Check, Loader2, RefreshCw, Sparkles, Undo2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/primitives/metric-card";
import { Sparkline } from "@/components/primitives/sparkline";
import { FlagRow } from "@/components/primitives/flag-row";
import { IntersectionPill } from "@/components/primitives/verdict-tags";
import { LifecycleChip } from "@/components/primitives/lifecycle-chip";
import { PropertyIcon } from "@/components/primitives/property-chip";
import { ApiError } from "@/lib/api";
import {
  useDisposition,
  useIssueState,
  useProductView,
  useSuggestIssues,
  type ClusterView,
  type FlagView,
} from "@/lib/data";
import { useFlagStore } from "@/lib/flag-store";
import type { FlagState, IntersectionTag, PropertyKind } from "@/lib/types";
import { cn } from "@/lib/utils";

type Grouping = "issue" | "cluster" | "property";

const GROUPING_LABEL: Record<Grouping, string> = {
  issue: "By issue",
  cluster: "By cluster",
  property: "By property",
};

/** An issue grouping the analyst ungrouped this session: keeps the in-place
 *  Undo available until reload (after a reload the rejected parent simply
 *  does not render and its members show flat). */
interface UngroupedIssue {
  id: string;
  label: string;
}

export default function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const {
    summary,
    metrics,
    clusters,
    issueClusters,
    hasIssueRows,
    views,
    isLoading,
    apiDown,
  } = useProductView(id);
  const [groupingChoice, setGroupingChoice] = useState<Grouping | null>(null);
  const [ungrouped, setUngrouped] = useState<UngroupedIssue[]>([]);
  const suggest = useSuggestIssues(id);
  const autoFired = useRef(false);

  // By issue is the default whenever the run has AI groupings to show.
  const hasIssueGroups = issueClusters.some((c) => c.kind === "issue");
  const grouping: Grouping =
    groupingChoice ?? (hasIssueGroups ? "issue" : "cluster");

  // Self-healing auto-suggest: runs that predate route-level auto-suggestion
  // have wording clusters but zero issue rows; generate once, silently.
  const runId = summary?.runId ?? null;
  const runSettled =
    summary?.status === "flagged" || summary?.status === "clear";
  const wordingCount = clusters.filter((c) => c.id !== "unclustered").length;
  useEffect(() => {
    if (autoFired.current || !runId || !runSettled) return;
    if (hasIssueRows || wordingCount < 2) return;
    autoFired.current = true;
    suggest.mutate(runId); // silent on failure by design
  }, [runId, runSettled, hasIssueRows, wordingCount, suggest]);

  if (isLoading) {
    return (
      <main className="flex flex-col gap-3 px-11 pb-14 pt-7">
        <div className="h-5 w-56 animate-pulse rounded-sm bg-surface" />
        <div className="h-24 animate-pulse rounded-lg border border-border bg-surface" />
        <div className="h-64 animate-pulse rounded-lg border border-border bg-surface" />
      </main>
    );
  }

  if (!summary) {
    return (
      <main className="px-11 pt-9 text-sm text-muted-foreground">
        {apiDown ? "The API is unreachable." : "Product not found."}{" "}
        <Link href="/" className="text-primary hover:underline">
          Back to dashboard
        </Link>
      </main>
    );
  }

  return (
    <main className="flex flex-col px-11 pb-14 pt-7">
      <div className="mb-3.5 text-xs text-muted-foreground">
        <Link href="/" className="text-primary hover:underline">
          Dashboard
        </Link>{" "}
        <span className="text-border">›</span> {summary.name}
      </div>

      <div className="mb-5 flex items-start justify-between">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-xl font-medium tracking-tight">{summary.name}</h1>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {summary.coverage.map((c) => (
              <span
                key={c.kind}
                className="inline-flex h-[22px] items-center gap-1.5 rounded-sm border border-border bg-surface px-2 font-mono text-[11px] font-medium text-foreground/70"
              >
                <PropertyIcon kind={c.kind} className="size-3" />
                {c.label}
              </span>
            ))}
            {summary.lastChecked ? (
              <span>{summary.lastChecked.toLowerCase()}</span>
            ) : null}
          </div>
        </div>
        <Button variant="outline" className="gap-2">
          <RefreshCw className="size-3.5" />
          Re-run
        </Button>
      </div>

      {metrics.length > 0 ? (
        <div className="mb-6 grid grid-cols-4 gap-3">
          {metrics.map((m) => (
            <MetricCard
              key={m.id}
              label={m.label}
              intent={m.intent}
              value={m.value}
              sublabel={m.sublabel}
              sparkline={
                m.sparkline ? (
                  <Sparkline data={m.sparkline} kind={m.sparklineKind} />
                ) : undefined
              }
            />
          ))}
        </div>
      ) : null}

      {views.length === 0 ? (
        <NoFlags
          checking={
            summary.status === "running" || summary.status === "awaiting_input"
          }
        />
      ) : (
        <>
          <div className="mb-3.5 flex items-center gap-3">
            <span className="flex-1 text-[13px] font-semibold">
              {views.length} flags in {wordingCount} clusters
            </span>
            <div className="flex rounded-md bg-muted p-[3px]">
              {(["issue", "cluster", "property"] as const).map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setGroupingChoice(g)}
                  className={cn(
                    "flex h-7 items-center whitespace-nowrap rounded-sm px-3 text-xs",
                    grouping === g
                      ? "bg-background font-semibold shadow-sm"
                      : "font-medium text-muted-foreground"
                  )}
                >
                  {GROUPING_LABEL[g]}
                </button>
              ))}
            </div>
          </div>

          {grouping === "issue" ? (
            <div className="flex flex-col gap-3.5">
              {ungrouped.map((u) => (
                <UngroupedBanner
                  key={u.id}
                  issue={u}
                  productId={id}
                  onRestored={() =>
                    setUngrouped((prev) => prev.filter((x) => x.id !== u.id))
                  }
                />
              ))}
              {issueClusters.map((c) =>
                c.kind === "issue" ? (
                  <IssueClusterGroup
                    key={c.id}
                    cluster={c}
                    views={views}
                    productId={id}
                    onUngrouped={() =>
                      setUngrouped((prev) =>
                        prev.some((x) => x.id === c.id)
                          ? prev
                          : [...prev, { id: c.id, label: c.label }]
                      )
                    }
                  />
                ) : (
                  <ClusterGroup
                    key={c.id}
                    label={c.label}
                    sourceLine={c.sourceLine}
                    dominantTag={c.dominantTag}
                    views={memberViews(c, views)}
                    productId={id}
                  />
                )
              )}
            </div>
          ) : grouping === "cluster" ? (
            <div className="flex flex-col gap-3.5">
              {clusters.map((c) => (
                <ClusterGroup
                  key={c.id}
                  label={c.label}
                  sourceLine={c.sourceLine}
                  dominantTag={c.dominantTag}
                  views={memberViews(c, views)}
                  productId={id}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-3.5">
              {groupByProperty(views).map(([kind, group]) => (
                <div
                  key={kind}
                  className="overflow-hidden rounded-lg border border-border bg-background"
                >
                  <div className="flex items-center gap-2.5 border-b border-border/60 bg-surface px-5 py-3.5">
                    <span className="flex size-6 items-center justify-center rounded-sm border border-border bg-background text-muted-foreground">
                      <PropertyIcon kind={kind} />
                    </span>
                    <span className="flex-1 text-[13px] font-semibold">
                      {group[0].property.url_or_handle}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {group.length} {group.length === 1 ? "flag" : "flags"}
                    </span>
                  </div>
                  <div className="divide-y divide-border/60">
                    {group.map((v) => (
                      <FlagRow key={v.flag.id} view={v} productId={id} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}

function ClusterGroup({
  label,
  sourceLine,
  dominantTag,
  views,
  productId,
}: {
  label: string;
  sourceLine: string;
  dominantTag: IntersectionTag;
  views: FlagView[];
  productId: string;
}) {
  const lifecycles = useFlagStore((s) => s.lifecycles);
  const disposition = useDisposition(productId);
  const flagIds = useMemo(() => views.map((v) => v.flag.id), [views]);
  const stateOf = (fid: string): FlagState =>
    lifecycles[fid]?.state ??
    views.find((v) => v.flag.id === fid)?.flag.state ??
    "open";
  const openIds = flagIds.filter((fid) => stateOf(fid) === "open");
  const [expanded, setExpanded] = useState(views.length <= 8);

  async function bulk(action: "confirm" | "dismiss") {
    // sequential to keep the API and score recompute orderly
    for (const fid of openIds) {
      try {
        await disposition.mutateAsync({ flagId: fid, action });
      } catch {
        // per-flag errors surface inline via the store; keep going
      }
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-background">
      <div className="flex items-center gap-2.5 border-b border-border/60 bg-surface px-5 py-3.5">
        <IntersectionPill tag={dominantTag} />
        <div className="flex min-w-0 flex-1 flex-col leading-snug">
          <span className="text-[13px] font-semibold">{label}</span>
          <span className="text-xs text-muted-foreground">
            <SourceLine text={sourceLine} />
          </span>
        </div>
        {openIds.length > 0 ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground"
              disabled={disposition.isPending}
              onClick={() => bulk("dismiss")}
            >
              Dismiss all
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={disposition.isPending}
              onClick={() => bulk("confirm")}
            >
              Confirm all
            </Button>
          </>
        ) : (
          <ClusterStateChip
            states={flagIds.map((fid) => stateOf(fid))}
            team={
              flagIds.map((fid) => lifecycles[fid]?.team).find((t) => t) ??
              null
            }
          />
        )}
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          {expanded ? "Collapse" : `Show ${views.length}`}
        </button>
      </div>
      {expanded ? (
        <div className="divide-y divide-border/60">
          {views.map((v) => (
            <FlagRow key={v.flag.id} view={v} productId={productId} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function memberViews(c: ClusterView, views: FlagView[]): FlagView[] {
  return c.flagIds
    .map((fid) => views.find((v) => v.flag.id === fid))
    .filter((v): v is FlagView => v !== undefined);
}

/** An AI issue grouping (suggested and confirmed render identically:
 *  grouping is a view, not a decision). The rationale is always in plain
 *  sight (the explainability contract: the analyst must see WHY it grouped);
 *  the only action is a reversible Ungroup. Member wording clusters render
 *  nested inside with their own rows and bulk actions. */
function IssueClusterGroup({
  cluster,
  views,
  productId,
  onUngrouped,
}: {
  cluster: ClusterView;
  views: FlagView[];
  productId: string;
  onUngrouped: () => void;
}) {
  const issueState = useIssueState(productId);
  const [expanded, setExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function ungroup() {
    setError(null);
    try {
      await issueState.mutateAsync({
        clusterId: cluster.id,
        state: "rejected",
      });
      onUngrouped();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "The API is unreachable."
      );
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-background">
      <div className="flex items-center gap-2.5 border-b border-border/60 bg-surface px-5 py-3.5">
        <IntersectionPill tag={cluster.dominantTag} />
        <div className="flex min-w-0 flex-1 flex-col leading-snug">
          <span className="flex items-center gap-2 text-[13px] font-semibold">
            {cluster.label}
            <Badge
              variant="secondary"
              className="gap-1 bg-accent font-medium text-accent-foreground"
            >
              <Sparkles className="size-3" />
              AI grouped
            </Badge>
          </span>
          <span className="text-xs text-muted-foreground">
            <SourceLine text={cluster.sourceLine} />
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground"
          disabled={issueState.isPending}
          onClick={ungroup}
        >
          {issueState.isPending ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : null}
          Ungroup
        </Button>
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          {expanded ? "Collapse" : `Show ${cluster.members.length} clusters`}
        </button>
      </div>
      {cluster.rationale ? (
        <p className="border-b border-border/60 px-5 py-3 text-xs leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground/80">Why grouped: </span>
          {cluster.rationale}
        </p>
      ) : null}
      {error ? (
        <p className="border-b border-border/60 px-5 py-2 text-xs text-danger-text">
          {error}
        </p>
      ) : null}
      {expanded ? (
        <div className="flex flex-col gap-2.5 bg-surface/60 p-3">
          {cluster.members.map((m) => (
            <ClusterGroup
              key={m.id}
              label={m.label}
              sourceLine={m.sourceLine}
              dominantTag={m.dominantTag}
              views={memberViews(m, views)}
              productId={productId}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** Session-scoped replacement for an ungrouped issue card: keeps the undo
 *  one click away, exactly where the card was. */
function UngroupedBanner({
  issue,
  productId,
  onRestored,
}: {
  issue: UngroupedIssue;
  productId: string;
  onRestored: () => void;
}) {
  const issueState = useIssueState(productId);
  const [error, setError] = useState<string | null>(null);

  async function undo() {
    setError(null);
    try {
      await issueState.mutateAsync({
        clusterId: issue.id,
        state: "suggested",
      });
      onRestored();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "The API is unreachable."
      );
    }
  }

  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-dashed border-border bg-surface px-5 py-2">
      <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
        <span className="font-medium text-foreground/80">{issue.label}</span>
        {" · "}Ungrouped by you
      </span>
      {error ? <span className="text-xs text-danger-text">{error}</span> : null}
      <Button
        variant="ghost"
        size="sm"
        className="gap-1.5"
        disabled={issueState.isPending}
        onClick={undo}
      >
        {issueState.isPending ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <Undo2 className="size-3.5" />
        )}
        Undo
      </Button>
    </div>
  );
}

function ClusterStateChip({
  states,
  team,
}: {
  states: FlagState[];
  team: string | null;
}) {
  const unique = Array.from(new Set(states));
  if (unique.length === 1) {
    return <LifecycleChip state={unique[0]} team={team} />;
  }
  return (
    <span className="text-xs text-muted-foreground">all dispositioned</span>
  );
}

function SourceLine({ text }: { text: string }) {
  // Rule and entry ids render in the mono face (DESIGN.md typography rule).
  const parts = text.split(/(R-0\d(?:-[A-Z]+)?|D-0\d)/g);
  return (
    <>
      {parts.map((p, i) =>
        /^(R-0\d(-[A-Z]+)?|D-0\d)$/.test(p) ? (
          <span key={i} className="font-mono">
            {p}
          </span>
        ) : (
          <span key={i}>{p}</span>
        )
      )}
    </>
  );
}

function groupByProperty(views: FlagView[]): [PropertyKind, FlagView[]][] {
  const order: PropertyKind[] = ["website", "instagram", "facebook"];
  const map = new Map<PropertyKind, FlagView[]>();
  for (const v of views) {
    const k = v.property.kind;
    if (!map.has(k)) map.set(k, []);
    map.get(k)!.push(v);
  }
  return order
    .filter((k) => map.has(k))
    .map((k) => [k, map.get(k)!] as [PropertyKind, FlagView[]]);
}

function NoFlags({ checking }: { checking: boolean }) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-lg border border-border px-6 py-8 text-center">
      <span className="flex size-6 items-center justify-center rounded-pill border border-success/30 bg-success-bg">
        <Check className="size-3 text-success" />
      </span>
      <span className="text-[13px] font-semibold">
        {checking ? "Check in progress" : "No open flags"}
      </span>
      <span className="text-xs text-muted-foreground">
        {checking
          ? "Results land here as checks complete."
          : "All checks passing. The daily check keeps watching for drift."}
      </span>
    </div>
  );
}
