// meta: single render helper for VERBATIM scorecard rule text (doc 05 §1).
// Guardrail: rule text is stored byte-for-byte, including markdown [text](url)
// syntax; ONLY rendering may transform it. This helper displays markdown links
// as styled anchors and everything else untouched. Every surface that renders
// rule text must go through <RuleText/>; never store a flattened variant.

const MD_LINK = /\[([^\]]+)\]\(([^)\s]+)\)/g;

export function RuleText({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let i = 0;
  for (const m of text.matchAll(MD_LINK)) {
    const idx = m.index ?? 0;
    if (idx > last) nodes.push(<span key={i++}>{text.slice(last, idx)}</span>);
    nodes.push(
      <a
        key={i++}
        href={m[2]}
        target="_blank"
        rel="noreferrer"
        className="text-primary underline underline-offset-2 hover:text-accent-foreground"
      >
        {m[1]}
      </a>
    );
    last = idx + m[0].length;
  }
  if (last < text.length) nodes.push(<span key={i++}>{text.slice(last)}</span>);
  return <span className={className}>{nodes}</span>;
}
