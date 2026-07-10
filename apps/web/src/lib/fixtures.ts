// meta: fixture dataset for M5 frontend (Lane B). Derived from the FROZEN
// ground truth at ground-truth/ground_truth.json (records GT-P05-01, GT-P07-01,
// GT-F03, GT-P45-01, GT-P18-01, GT-P08-01, GT-P10-01 et al), the v2.2 delta PDF
// (metric card contents, verdict tag rows, lifecycle states) and the UX v2
// prototype (layout copy). Shapes conform to src/lib/types.ts (frozen contract).
// Rule text is VERBATIM from doc 05 §1; never paraphrase it. Surfaces must not
// import this file directly; they read through src/lib/data.ts (the one-file
// M4 API swap point). Dev-time stand-in only; swapped for live API data at
// integration.

import type {
  BinaryCheck,
  Flag,
  FlagState,
  IntersectionTag,
  Material,
  Property,
  PropertyKind,
  Rule,
  RunScores,
  Severity,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// View-model types (fixture-layer only; the frozen contract stays in types.ts)
// ---------------------------------------------------------------------------

export type ProductStatus = "flagged" | "clear" | "checking" | "empty";

export interface PropertyCoverage {
  kind: PropertyKind;
  label: string; // e.g. "20 pages", "17 posts"
}

export interface ProductSummary {
  id: string;
  name: string;
  status: ProductStatus;
  verifiedScore: number | null;
  scoreTrend: number[]; // verified score per run (runs.scores time series)
  openFlagCount: number;
  note: string; // AI summary note on the card
  coverage: PropertyCoverage[];
  assignmentNote: string | null;
  lastChecked: string | null;
  checking: { done: number; total: number; step: string; pct: number } | null;
}

export interface SublabelPart {
  text: string;
  tone?: "danger" | "warning" | "success";
}

export interface MetricFixture {
  id: string;
  label: string;
  intent: string; // tooltip line (delta PDF / 01_spec §10)
  value: string;
  delta?: { text: string; tone: "success" | "danger" };
  sublabel: SublabelPart[];
  sparkline?: number[];
  sparklineKind?: "area" | "line";
}

export interface ClusterFixture {
  id: string;
  productId: string;
  label: string;
  sourceLine: string; // e.g. "R-01 · 6 flags: 4 pages, 2 Instagram posts"
  dominantTag: IntersectionTag;
  flagIds: string[];
}

export interface WhyStep {
  title: string;
  detail?: string; // present on the expandable step
}

export interface FlagMeta {
  flagId: string;
  title: string; // short finding title (flag detail header)
  explainer: string; // one-line explainer under the tags
  severity: Severity;
  foundAt: string;
  model: string;
  missingRequirement: string | null; // "required nearby, not found" callout
  chain: WhyStep[]; // compact why-flagged chain, 5 steps
  postDate: string | null; // social posts only
}

// ---------------------------------------------------------------------------
// Scorecard: 4 rules VERBATIM from doc 05 §1 + decomposed checks + D-01.
// R-01 keeps the source's markdown [text](url) link markup byte-for-byte;
// rendering (links as anchors) happens ONLY via lib/render-rule-text.tsx.
// ---------------------------------------------------------------------------

export const rules: Rule[] = [
  {
    id: "R-01",
    verbatim_text:
      "If Turbotax free is mentioned, the following must be disclosed right underneath ~37% of filers qualify. [Simple Form 1040 returns only](https://turbotax.intuit.com/personal-taxes/online/free-edition.jsp#modals/simple-tax-returns-en) (no schedules, except for EITC, CTC, student loan interest, and Schedule 1-A).",
    severity: "High",
    position: 1,
  },
  {
    id: "R-02",
    verbatim_text:
      "If a rate of finance charge was stated, was the finance charge stated as an APR?",
    severity: "High",
    position: 2,
  },
  {
    id: "R-03",
    verbatim_text:
      "If the product being advertised is a deposit product, does the FDIC insurance language state Deposit product is FDIC-insured up to $250,000 through  Bank",
    severity: "Medium",
    position: 3,
  },
  {
    id: "R-04",
    verbatim_text:
      'If an institution states a bonus in an advertisement, does the advertisement state clearly and conspicuously the following information, if applicable to the advertised product: (1) "Annual percentage yield," using that term; (2) Time requirement to obtain the bonus; (3) Minimum balance required to obtain the bonus; (4) Minimum balance required to open the account, if it is greater than the minimum balance necessary to obtain the bonus; and (5) Time when the bonus will be provided? In addition, general statements such as "bonus checking" or "get a bonus when you open a checking account" do not trigger the bonus disclosures.',
    severity: "Medium",
    position: 4,
  },
];

export const D01_APPROVED_TEXT =
  "~37% of filers qualify. Simple Form 1040 returns only (no schedules, except for EITC, CTC, student loan interest, and Schedule 1-A).";

export const checks: BinaryCheck[] = [
  {
    id: "R-01.1",
    rule_id: "R-01",
    kind: "trigger",
    text: "Trigger: content mentions TurboTax Free or Free Edition. Yes/no.",
    evidence_criteria: "The mentioning phrase, quoted",
    library_entry_id: null,
  },
  {
    id: "R-01.2",
    rule_id: "R-01",
    kind: "requirement",
    text: "Requirement: the approved disclosure appears right underneath the mention. Yes/no.",
    evidence_criteria: "The disclosure text found, or the nearest text where it should be",
    library_entry_id: "D-01",
  },
  {
    id: "R-03.1",
    rule_id: "R-03",
    kind: "trigger",
    text: "Trigger: the advertised product is a deposit product. Yes/no.",
    evidence_criteria: "The deposit-product phrase, quoted",
    library_entry_id: null,
  },
  {
    id: "R-03.2",
    rule_id: "R-03",
    kind: "requirement",
    text: "Requirement: the FDIC insurance language states the deposit product is FDIC-insured up to $250,000 through the partner bank. Yes/no.",
    evidence_criteria: "The FDIC language found, quoted",
    library_entry_id: null,
  },
];

// ---------------------------------------------------------------------------
// Products, properties, run
// ---------------------------------------------------------------------------

export const TURBOTAX_ID = "turbotax-free";
export const RUN_ID = "run-042";

export const properties: Property[] = [
  { id: "prop-web", kind: "website", url_or_handle: "turbotax.intuit.com", config: { crawl_depth: 2, page_cap: 20 } },
  { id: "prop-ig", kind: "instagram", url_or_handle: "@turbotax", config: { timeframe: "Feb 1 to Mar 31" } },
  { id: "prop-fb", kind: "facebook", url_or_handle: "facebook.com/turbotax", config: { intake: "pasted" } },
];

export const products: ProductSummary[] = [
  {
    id: TURBOTAX_ID,
    name: "TurboTax Free",
    status: "flagged",
    verifiedScore: 79,
    scoreTrend: [72, 74, 73, 78, 81, 77, 79],
    openFlagCount: 8,
    note: "Free-filing claims missing the eligibility disclosure; footer disclosure drifted from approved wording yesterday.",
    coverage: [
      { kind: "website", label: "20 pages" },
      { kind: "instagram", label: "17 posts" },
      { kind: "facebook", label: "9 posts" },
    ],
    assignmentNote: "2 flags assigned to Web",
    lastChecked: "Checked today 09:12",
    checking: null,
  },
  {
    id: "quickbooks-money",
    name: "QuickBooks Money",
    status: "clear",
    verifiedScore: 93,
    scoreTrend: [78, 78, 82, 82, 87, 89, 93],
    openFlagCount: 0,
    note: "All checks passing. Bonus-disclosure wording matches the approved library entry.",
    coverage: [
      { kind: "website", label: "14 pages" },
      { kind: "instagram", label: "11 posts" },
    ],
    assignmentNote: null,
    lastChecked: "Checked today 09:05",
    checking: null,
  },
  {
    id: "credit-karma-money",
    name: "Credit Karma Money",
    status: "checking",
    verifiedScore: null,
    scoreTrend: [],
    openFlagCount: 0,
    note: "",
    coverage: [],
    assignmentNote: null,
    lastChecked: null,
    checking: {
      done: 47,
      total: 66,
      step: "running R-03 against instagram posts",
      pct: 71,
    },
  },
];

export const runScores: RunScores = {
  draft: 74,
  verified: 79,
  per_property: { "prop-web": 72, "prop-ig": 86, "prop-fb": 84 },
};

// ---------------------------------------------------------------------------
// Hero metrics (U2) and product metric row (U6) — contents per the v2.2 delta
// PDF (Delta 1, canonical over the prototype). Intent lines are the tooltips.
// ---------------------------------------------------------------------------

export const heroMetrics: MetricFixture[] = [
  {
    id: "portfolio-score",
    label: "Verified portfolio score",
    intent: "Are we getting safer or riskier overall?",
    value: "84",
    delta: { text: "▴3", tone: "success" },
    sublabel: [{ text: "verified, 7-day trend" }],
    sparkline: [78, 79, 80, 80, 81, 82, 84],
    sparklineKind: "area",
  },
  {
    id: "open-violations",
    label: "Open violations",
    intent: "What's exposed right now and how long has it festered?",
    value: "11",
    sublabel: [{ text: "3 high", tone: "danger" }, { text: " · oldest open 6 days" }],
  },
  {
    id: "awaiting-triage",
    label: "Awaiting triage",
    intent: "Is the review queue under control?",
    value: "7",
    sublabel: [{ text: "median disposition 0.8 days" }],
  },
  {
    id: "coverage",
    label: "Coverage 24h",
    intent: "Can we attest to what's live right now?",
    value: "96%",
    sublabel: [{ text: "71 live assets tracked" }],
  },
  {
    id: "caught-this-week",
    label: "Caught this week",
    intent: "Is anything shipping around the approval process?",
    value: "5",
    sublabel: [{ text: "3 unapproved · 2 drift" }],
  },
];

export const productMetrics: Record<string, MetricFixture[]> = {
  [TURBOTAX_ID]: [
    {
      id: "verified-score",
      label: "Verified score",
      intent: "Are we getting safer or riskier overall?",
      value: "79",
      sublabel: [{ text: "draft 74 · 8 of 11 dispositioned" }],
      sparkline: [72, 74, 73, 78, 81, 77, 79],
      sparklineKind: "line",
    },
    {
      id: "open-violations",
      label: "Open violations",
      intent: "What's exposed right now and how long has it festered?",
      value: "8",
      sublabel: [{ text: "3 high", tone: "danger" }, { text: " · oldest 6d" }],
    },
    {
      id: "awaiting-triage",
      label: "Awaiting triage",
      intent: "Is the review queue under control?",
      value: "3",
      sublabel: [{ text: "median 0.8d" }],
    },
    {
      id: "coverage",
      label: "Coverage 24h",
      intent: "Can we attest to what's live right now?",
      value: "100%",
      sublabel: [{ text: "46 assets, 3 pasted" }],
    },
  ],
};

// ---------------------------------------------------------------------------
// Materials. extracted_text always contains the flag's evidence_quote as a
// substring (the programmatic evidence-validity contract from 01_spec §4).
// Quotes and reasoning come from the frozen ground truth records.
// ---------------------------------------------------------------------------

export const materials: Material[] = [
  {
    id: "mat-p05",
    property_id: "prop-web",
    ref: "turbotax.intuit.com/personal-taxes/online/",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "gt-p05",
    extracted_text:
      "File your own taxes\nDo it yourself with expert help as you go.\n$0-$139 State additional for paid products. Start for free. Pay only when you file.\nSwitching to TurboTax is easy. Just upload last year's return to get started.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-p07",
    property_id: "prop-web",
    ref: "turbotax.intuit.com/personal-taxes/compare/online/",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "gt-p07",
    extracted_text:
      "Compare TurboTax products\nDo it yourself\n$0-$139 State additional for paid products. Start for free. Pay only when you file.\nFull Service, an expert does your taxes for you, $89-$449.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-p03",
    property_id: "prop-web",
    ref: "turbotax.intuit.com/free-edition",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "gt-f03-page",
    extracted_text:
      "TurboTax Free Edition\nTurboTax Free Edition ($0 Federal + $0 State + $0 To File) is available for those filing simple Form 1040 returns only (no forms or schedules except as needed to claim the Earned Income Tax Credit, Child Tax Credit, student loan interest, and Schedule 1-A). More details are available here. Roughly 37% of taxpayers qualify.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-p04",
    property_id: "prop-web",
    ref: "turbotax.intuit.com/personal-taxes/online",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "tt-004-hero",
    extracted_text:
      "Taxes done right, however you choose.\nFile your taxes for free with TurboTax Free Edition.\nAnswer simple questions and we'll guide you through filing step by step.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-ig-mar4",
    property_id: "prop-ig",
    ref: "IG post, Mar 4",
    kind: "post",
    modality: "social_post",
    media_ref: null,
    content_hash: "ig-mar4",
    extracted_text:
      "Maximum refund guaranteed. File with TurboTax and get every dollar you deserve. Link in bio.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-ig-feb12",
    property_id: "prop-ig",
    ref: "IG post, Feb 12",
    kind: "post",
    modality: "social_post",
    media_ref: null,
    content_hash: "ig-feb12",
    extracted_text:
      "100% free to file. Yes, really. Simple returns only. See if you qualify at the link in bio.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-footer",
    property_id: "prop-web",
    ref: "shared footer block (44 pages)",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "gt-f03",
    extracted_text:
      "TurboTax Free Edition ($0 Federal + $0 State + $0 To File) is available for those filing simple Form 1040 returns only (no forms or schedules except as needed to claim the Earned Income Tax Credit, Child Tax Credit, student loan interest, and Schedule 1-A). More details are available here. Roughly 37% of taxpayers qualify.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-p45",
    property_id: "prop-web",
    ref: "turbotax.intuit.com/es/",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "gt-p45",
    extracted_text:
      "Declara tus impuestos con confianza.\nGratis para declaraciones simples con Formulario 1040 ... Aproximadamente el 37% de los contribuyentes califica.\nComienza gratis hoy.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-p18",
    property_id: "prop-web",
    ref: "turbotax.intuit.com/credit-karma-money/",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "gt-p18",
    extracted_text:
      "Protect your money\nLock your debit card instantly, dispute transactions in-app, and get FDIC insurance up to $5M through a network of participating banks.\nFree to open. No monthly fees. No minimum balance.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-p08",
    property_id: "prop-web",
    ref: "turbotax.intuit.com/personal-taxes/online/military-edition.jsp",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "gt-p08",
    extracted_text:
      "TurboTax for military\nMore about our free military tax filing discount ... eligible U.S. enlisted active duty and reserve file free.\nSimply enter your W-2 and verify your military rank when prompted.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
  {
    id: "mat-p10",
    property_id: "prop-web",
    ref: "blog.turbotax.intuit.com/turbotax-news/military-free-filing",
    kind: "page",
    modality: "text",
    media_ref: null,
    content_hash: "gt-p10",
    extracted_text:
      "TurboTax offers free tax filing for military active duty and reserve.\nEligible U.S. enlisted active duty and reserve personnel can file free with TurboTax.\nThe offer covers federal and state returns.",
    fetched_at: "2026-07-10T09:12:00Z",
  },
];

// ---------------------------------------------------------------------------
// Flags. 11 flags in 3 clusters (prototype 3e composition); verdict tag rows
// for TT-004, TT-003 and TT-005 follow the delta PDF's three demonstration
// rows exactly (including the Approved but non-compliant case).
// ---------------------------------------------------------------------------

function verdicts(v: {
  check: string;
  material: string;
  trigger: boolean;
  requirement: boolean | null;
  a: boolean;
  b: boolean | null;
  tag: IntersectionTag;
  quote: string;
  location: string;
  reason: string;
  confidence: number;
}) {
  return {
    material_id: v.material,
    check_id: v.check,
    trigger_met: v.trigger,
    requirement_met: v.requirement,
    axis_a: v.a,
    axis_b: v.b,
    intersection_tag: v.tag,
    evidence_quote: v.quote,
    location: v.location,
    reason: v.reason,
    confidence: v.confidence,
  };
}

function flag(f: {
  id: string;
  material: string;
  check: string;
  state: FlagState;
  team?: string | null;
  note?: string | null;
  cluster: string;
  modality?: "text" | "social_post";
  v: Parameters<typeof verdicts>[0];
}): Flag {
  return {
    id: f.id,
    run_id: RUN_ID,
    material_id: f.material,
    check_id: f.check,
    state: f.state,
    assigned_team: f.team ?? null,
    note: f.note ?? null,
    modality: f.modality ?? "text",
    media_ref: null,
    cluster_id: f.cluster,
    verdicts: verdicts(f.v),
  };
}

export const flags: Flag[] = [
  // Cluster 1: "File free" claims missing the eligibility disclosure (R-01)
  flag({
    id: "TT-004",
    material: "mat-p04",
    check: "R-01.2",
    state: "assigned",
    team: "Web",
    note: "Flagged for legal, template-level fix",
    cluster: "cl-free-claims",
    v: {
      check: "R-01.2",
      material: "mat-p04",
      trigger: true,
      requirement: false,
      a: false,
      b: false,
      tag: "unapproved_violation",
      quote: "File your taxes for free with TurboTax Free Edition.",
      location: "/personal-taxes/online · hero",
      reason: "No qualifying disclosure anywhere on the page.",
      confidence: 0.95,
    },
  }),
  flag({
    id: "TT-001",
    material: "mat-p05",
    check: "R-01.2",
    state: "open",
    cluster: "cl-free-claims",
    v: {
      check: "R-01.2",
      material: "mat-p05",
      trigger: true,
      requirement: false,
      a: false,
      b: false,
      tag: "unapproved_violation",
      quote: "$0-$139 State additional for paid products. Start for free. Pay only when you file.",
      location: "/personal-taxes/online/ · Do It Yourself pricing card",
      reason:
        "The $0 bottom of the DIY price range is TurboTax Free Edition; no eligibility disclosure right underneath. The 37% language exists only in the shared footer, far from the claim.",
      confidence: 0.7,
    },
  }),
  flag({
    id: "TT-002",
    material: "mat-p07",
    check: "R-01.2",
    state: "open",
    cluster: "cl-free-claims",
    v: {
      check: "R-01.2",
      material: "mat-p07",
      trigger: true,
      requirement: false,
      a: false,
      b: false,
      tag: "unapproved_violation",
      quote: "$0-$139 State additional for paid products. Start for free. Pay only when you file.",
      location: "/personal-taxes/compare/online/ · Do It Yourself pricing card",
      reason:
        "Same pattern as the online hub: free-tier price advertised on the comparison page without adjacent eligibility disclosure; 37% language footer-only.",
      confidence: 0.7,
    },
  }),
  flag({
    id: "TT-003",
    material: "mat-p03",
    check: "R-01.2",
    state: "fix_pending_verification",
    team: "Web",
    note: "Restore approved wording verbatim",
    cluster: "cl-free-claims",
    v: {
      check: "R-01.2",
      material: "mat-p03",
      trigger: true,
      requirement: true,
      a: true,
      b: false,
      tag: "drifted_but_compliant",
      quote: "Roughly 37% of taxpayers qualify.",
      location: "/free-edition · footer",
      reason:
        "The footer footnote carries the substance of the approved disclosure but the wording drifts from D-01: 'Roughly 37% of taxpayers qualify' vs approved '~37% of filers qualify'.",
      confidence: 1.0,
    },
  }),
  flag({
    id: "TT-005",
    material: "mat-ig-mar4",
    check: "R-01.2",
    state: "open",
    cluster: "cl-free-claims",
    modality: "social_post",
    v: {
      check: "R-01.2",
      material: "mat-ig-mar4",
      trigger: true,
      requirement: false,
      a: false,
      b: true,
      tag: "approved_but_non_compliant",
      quote: "Maximum refund guaranteed",
      location: "IG post · Mar 4",
      reason:
        "Published exactly as approved, but the approved wording itself omits the Free Edition $30 qualifier the scorecard requires alongside free-filing guarantee claims.",
      confidence: 0.85,
    },
  }),
  flag({
    id: "TT-006",
    material: "mat-ig-feb12",
    check: "R-01.2",
    state: "dismissed",
    note: "Covered by D-01 in bio link",
    cluster: "cl-free-claims",
    modality: "social_post",
    v: {
      check: "R-01.2",
      material: "mat-ig-feb12",
      trigger: true,
      requirement: false,
      a: false,
      b: false,
      tag: "unapproved_violation",
      quote: "100% free to file. Yes, really.",
      location: "IG post · Feb 12",
      reason: "Caption has no qualifier and the bio link was not checked at post time.",
      confidence: 0.6,
    },
  }),

  // Cluster 2: published disclosure drifted from approved wording (vs D-01)
  flag({
    id: "TT-007",
    material: "mat-footer",
    check: "R-01.2",
    state: "assigned",
    team: "Web",
    note: "Restore approved wording verbatim",
    cluster: "cl-drift",
    v: {
      check: "R-01.2",
      material: "mat-footer",
      trigger: true,
      requirement: true,
      a: true,
      b: false,
      tag: "drifted_but_compliant",
      quote:
        "TurboTax Free Edition ($0 Federal + $0 State + $0 To File) is available for those filing simple Form 1040 returns only (no forms or schedules except as needed to claim the Earned Income Tax Credit, Child Tax Credit, student loan interest, and Schedule 1-A). More details are available here. Roughly 37% of taxpayers qualify.",
      location: "shared footer, 'TurboTax Free Edition' offer footnote · appears on 44 pages",
      reason:
        "The footer's Free Edition footnote carries the substance of the approved disclosure but the wording drifts from library entry D-01: 'Roughly 37% of taxpayers qualify' vs approved '~37% of filers qualify', and the schedule-exception phrasing is restructured. Content-equivalent, wording-drifted.",
      confidence: 1.0,
    },
  }),
  flag({
    id: "TT-008",
    material: "mat-p45",
    check: "R-01.2",
    state: "open",
    cluster: "cl-drift",
    v: {
      check: "R-01.2",
      material: "mat-p45",
      trigger: true,
      requirement: true,
      a: true,
      b: false,
      tag: "drifted_but_compliant",
      quote: "declaraciones simples con Formulario 1040 ... Aproximadamente el 37% de los contribuyentes califica.",
      location: "Spanish homepage, free-tier module and footnotes",
      reason:
        "The Spanish homepage carries the eligibility disclosure translated; substance intact, wording necessarily differs from the English-only approved entry D-01. The library has no approved Spanish disclosure: a real gap this finding exposes.",
      confidence: 0.85,
    },
  }),

  // Cluster 3: claims live without a matching approved entry (reconciliation)
  flag({
    id: "TT-009",
    material: "mat-p18",
    check: "R-03.2",
    state: "open",
    cluster: "cl-unapproved",
    v: {
      check: "R-03.2",
      material: "mat-p18",
      trigger: true,
      requirement: false,
      a: false,
      b: null,
      tag: "unapproved_violation",
      quote:
        "Lock your debit card instantly, dispute transactions in-app, and get FDIC insurance up to $5M through a network of participating banks.",
      location: "body, 'Protect your money' feature card",
      reason:
        "The page leads with 'FDIC insurance up to $5M through a network of participating banks', a sweep-network formulation that names no insuring bank at the claim and states a different amount than the required per-bank $250,000 formulation. No approved library entry exists for FDIC language.",
      confidence: 1.0,
    },
  }),
  flag({
    id: "TT-010",
    material: "mat-p08",
    check: "R-01.2",
    state: "open",
    cluster: "cl-unapproved",
    v: {
      check: "R-01.2",
      material: "mat-p08",
      trigger: true,
      requirement: false,
      a: false,
      b: null,
      tag: "unapproved_violation",
      quote:
        "More about our free military tax filing discount ... eligible U.S. enlisted active duty and reserve file free.",
      location: "military edition page, offer module",
      reason:
        "A different free offer (military discount) with its own eligibility limits and no approved counterpart in the library. Either the library should gain an approved military-offer disclosure, or this is an unapproved free-claim variant.",
      confidence: 0.6,
    },
  }),
  flag({
    id: "TT-011",
    material: "mat-p10",
    check: "R-01.2",
    state: "open",
    cluster: "cl-unapproved",
    v: {
      check: "R-01.2",
      material: "mat-p10",
      trigger: true,
      requirement: false,
      a: false,
      b: null,
      tag: "unapproved_violation",
      quote: "Eligible U.S. enlisted active duty and reserve personnel can file free with TurboTax.",
      location: "military blog post body",
      reason:
        "Same class as the military edition page: military free-filing claim, no approved library counterpart.",
      confidence: 0.6,
    },
  }),
];

export const clusters: ClusterFixture[] = [
  {
    id: "cl-free-claims",
    productId: TURBOTAX_ID,
    label: '"File free" claims missing the eligibility disclosure',
    sourceLine: "R-01 · 6 flags: 4 pages, 2 Instagram posts",
    dominantTag: "unapproved_violation",
    flagIds: ["TT-004", "TT-001", "TT-002", "TT-003", "TT-005", "TT-006"],
  },
  {
    id: "cl-drift",
    productId: TURBOTAX_ID,
    label: "Published disclosure drifted from approved wording",
    sourceLine: "Reconciliation vs D-01 · 2 flags · footer block appears on 44 pages",
    dominantTag: "drifted_but_compliant",
    flagIds: ["TT-007", "TT-008"],
  },
  {
    id: "cl-unapproved",
    productId: TURBOTAX_ID,
    label: "Claims live without a matching approved entry",
    sourceLine: "Reconciliation · 3 flags",
    dominantTag: "unapproved_violation",
    flagIds: ["TT-009", "TT-010", "TT-011"],
  },
];

// ---------------------------------------------------------------------------
// Per-flag presentation metadata: titles, explainers, why-flagged chains.
// ---------------------------------------------------------------------------

const CHAIN_MODEL = "Groq Llama 3.3";

export const flagMeta: Record<string, FlagMeta> = {
  "TT-004": {
    flagId: "TT-004",
    title: "Free claim without eligibility disclosure",
    explainer: "A free-filing claim in the hero with no qualifying disclosure anywhere on the page.",
    severity: "High",
    foundAt: "found today 09:12",
    model: CHAIN_MODEL,
    missingRequirement: '"~37% of filers qualify..." (D-01)',
    postDate: null,
    chain: [
      { title: "Crawled · /personal-taxes/online reached at depth 1" },
      { title: "Extracted · hero and body copy, 412 words" },
      {
        title: "Trigger check · R-01.1 matched",
        detail:
          "Using the copy extracted in step 2, R-01's trigger matched: the page mentions \"TurboTax Free Edition\" in the hero. Because the trigger fired, step 4 became required.",
      },
      { title: "Requirement check · searched step-2 copy for D-01 wording, no match" },
      { title: `Verdict · fail, evidence cited from step 4 · ${CHAIN_MODEL}` },
    ],
  },
  "TT-001": {
    flagId: "TT-001",
    title: "Free-tier price card without adjacent disclosure",
    explainer: "The DIY pricing card advertises the free tier with the 37% language only in the distant footer.",
    severity: "High",
    foundAt: "found today 09:12",
    model: CHAIN_MODEL,
    missingRequirement: '"~37% of filers qualify..." (D-01)',
    postDate: null,
    chain: [
      { title: "Crawled · /personal-taxes/online/ reached at depth 1" },
      { title: "Extracted · pricing cards and body copy, 380 words" },
      {
        title: "Trigger check · R-01.1 matched",
        detail:
          "The $0 bottom of the DIY price range is TurboTax Free Edition, so the card advertises the free product. A reviewer could read '$0-$139' as a range price instead; this is the kind of flag the disposition gate exists to confirm or dismiss.",
      },
      { title: "Requirement check · no D-01 wording adjacent to the claim" },
      { title: `Verdict · fail at 0.7 confidence · ${CHAIN_MODEL}` },
    ],
  },
  "TT-002": {
    flagId: "TT-002",
    title: "Free-tier price card without adjacent disclosure",
    explainer: "Same pattern as the online hub, on the comparison page.",
    severity: "High",
    foundAt: "found today 09:12",
    model: CHAIN_MODEL,
    missingRequirement: '"~37% of filers qualify..." (D-01)',
    postDate: null,
    chain: [
      { title: "Crawled · /personal-taxes/compare/online/ reached at depth 2" },
      { title: "Extracted · comparison table and pricing cards, 495 words" },
      {
        title: "Trigger check · R-01.1 matched",
        detail:
          "Free-tier price advertised on the comparison page; the trigger fired on the Do It Yourself card's $0 price point.",
      },
      { title: "Requirement check · no D-01 wording adjacent to the claim" },
      { title: `Verdict · fail at 0.7 confidence · ${CHAIN_MODEL}` },
    ],
  },
  "TT-003": {
    flagId: "TT-003",
    title: "Footer disclosure drifted from approved wording",
    explainer: "The footnote keeps the substance of D-01 but the published wording has drifted.",
    severity: "High",
    foundAt: "found today 09:12",
    model: CHAIN_MODEL,
    missingRequirement: null,
    postDate: null,
    chain: [
      { title: "Crawled · /free-edition reached at depth 1" },
      { title: "Extracted · offer module and footer footnote, 340 words" },
      {
        title: "Trigger check · R-01.1 matched",
        detail: "The page mentions TurboTax Free Edition in the offer module and footer footnote.",
      },
      { title: "Requirement check · disclosure present; wording compared against D-01, drift found" },
      { title: `Verdict · compliant with drift, evidence cited from step 4 · ${CHAIN_MODEL}` },
    ],
  },
  "TT-005": {
    flagId: "TT-005",
    title: "Approved claim that violates the scorecard",
    explainer: "Published exactly as approved, but the approval itself violates the rules.",
    severity: "High",
    foundAt: "found today 09:14",
    model: CHAIN_MODEL,
    missingRequirement: '"(TurboTax Free Edition customers are entitled to payment of $30.)"',
    postDate: "Mar 4",
    chain: [
      { title: "Fetched · IG post of Mar 4 from the Feb 1 to Mar 31 window" },
      { title: "Extracted · caption, 14 words" },
      {
        title: "Trigger check · R-01.1 matched",
        detail:
          "The caption pairs the refund guarantee with the free-filing campaign. The published wording matches the approved claim verbatim, so axis B says matches approval; the scorecard still requires the Free Edition qualifier.",
      },
      { title: "Requirement check · required qualifier missing from caption and approved wording" },
      { title: `Verdict · fail, approval itself non-compliant · ${CHAIN_MODEL}` },
    ],
  },
  "TT-006": {
    flagId: "TT-006",
    title: "Free claim in caption without qualifier",
    explainer: "Caption has no qualifier; dismissed because D-01 is covered in the bio link.",
    severity: "High",
    foundAt: "found today 09:14",
    model: CHAIN_MODEL,
    missingRequirement: '"~37% of filers qualify..." (D-01)',
    postDate: "Feb 12",
    chain: [
      { title: "Fetched · IG post of Feb 12 from the Feb 1 to Mar 31 window" },
      { title: "Extracted · caption, 17 words" },
      {
        title: "Trigger check · R-01.1 matched",
        detail: "The caption claims 100% free filing, a TurboTax Free mention under R-01.",
      },
      { title: "Requirement check · no D-01 wording in the caption" },
      { title: `Verdict · fail, later dismissed at triage · ${CHAIN_MODEL}` },
    ],
  },
  "TT-007": {
    flagId: "TT-007",
    title: "Published footer drifted from D-01",
    explainer: "Published footer dropped the tilde and 'Simple', and restructured the schedule exceptions.",
    severity: "High",
    foundAt: "found today 09:12",
    model: CHAIN_MODEL,
    missingRequirement: null,
    postDate: null,
    chain: [
      { title: "Crawled · shared footer block detected on 44 of 46 pages" },
      { title: "Extracted · footer footnote judged once, inherited by every page containing it" },
      {
        title: "Trigger check · R-01.1 matched",
        detail:
          "The footnote mentions TurboTax Free Edition. Reconciliation compared the published wording against library entry D-01 with fuzzy matching.",
      },
      { title: "Requirement check · substance intact; wording drifted from D-01" },
      { title: `Verdict · drifted but compliant, one cluster for 44 pages · ${CHAIN_MODEL}` },
    ],
  },
  "TT-008": {
    flagId: "TT-008",
    title: "Spanish disclosure has no approved counterpart",
    explainer: "The translated disclosure keeps the substance; the library has no approved Spanish entry.",
    severity: "High",
    foundAt: "found today 09:12",
    model: CHAIN_MODEL,
    missingRequirement: null,
    postDate: null,
    chain: [
      { title: "Crawled · /es/ reached at depth 1" },
      { title: "Extracted · free-tier module and footnotes, 290 words" },
      {
        title: "Trigger check · R-01.1 matched",
        detail:
          "The Spanish homepage advertises free filing for simple returns. Reconciliation found no approved Spanish disclosure to compare against, so the English entry D-01 was used.",
      },
      { title: "Requirement check · substance intact in translation; wording differs from D-01" },
      { title: `Verdict · drifted but compliant, language-variant subclass · ${CHAIN_MODEL}` },
    ],
  },
  "TT-009": {
    flagId: "TT-009",
    title: "FDIC language does not match the required formulation",
    explainer: "A sweep-network FDIC claim that names no insuring bank and states a different amount.",
    severity: "Medium",
    foundAt: "found today 09:13",
    model: CHAIN_MODEL,
    missingRequirement: '"Deposit product is FDIC-insured up to $250,000 through [Bank]"',
    postDate: null,
    chain: [
      { title: "Crawled · /credit-karma-money/ reached at depth 2" },
      { title: "Extracted · feature cards and footnotes, 520 words" },
      {
        title: "Trigger check · R-03.1 matched",
        detail:
          "The advertised products are checking and savings accounts: deposit products ('Free to open', 'high-yield savings', 'overdraft coverage'). Because the trigger fired, the FDIC language requirement applies.",
      },
      { title: "Requirement check · required per-bank $250,000 formulation not found" },
      { title: `Verdict · fail, no approved library entry for FDIC language · ${CHAIN_MODEL}` },
    ],
  },
  "TT-010": {
    flagId: "TT-010",
    title: "Military free offer without approved counterpart",
    explainer: "A different free offer with its own eligibility limits and no approved library entry.",
    severity: "High",
    foundAt: "found today 09:13",
    model: CHAIN_MODEL,
    missingRequirement: null,
    postDate: null,
    chain: [
      { title: "Crawled · /personal-taxes/online/military-edition.jsp reached at depth 2" },
      { title: "Extracted · offer module, 310 words" },
      {
        title: "Trigger check · reconciliation matched a free-filing claim variant",
        detail:
          "Not a TurboTax Free Edition mention, so R-01's 37% disclosure does not straightforwardly apply; but it is a free-filing claim with no approved counterpart in the library.",
      },
      { title: "Requirement check · no approved military-offer disclosure exists" },
      { title: `Verdict · unapproved claim variant, review recommended · ${CHAIN_MODEL}` },
    ],
  },
  "TT-011": {
    flagId: "TT-011",
    title: "Military free-filing claim in blog post",
    explainer: "Same class as the military edition page; no approved library counterpart.",
    severity: "High",
    foundAt: "found today 09:13",
    model: CHAIN_MODEL,
    missingRequirement: null,
    postDate: null,
    chain: [
      { title: "Crawled · blog.turbotax.intuit.com military post reached at depth 2" },
      { title: "Extracted · post body, 640 words" },
      {
        title: "Trigger check · reconciliation matched a free-filing claim variant",
        detail: "The blog post repeats the military free-filing claim with no approved counterpart in the library.",
      },
      { title: "Requirement check · no approved military-offer disclosure exists" },
      { title: `Verdict · unapproved claim variant, review recommended · ${CHAIN_MODEL}` },
    ],
  },
};
