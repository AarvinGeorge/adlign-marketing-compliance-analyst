// meta: U3 New check modal (client Dialog, not a route). Product
// create-or-pick, freeform links textarea with detected PropertyChips
// (fixture mode: deterministic client-side extraction via data.ts, simulating
// N1's live chips; zero LLM, zero network), crawl depth / page cap / timeframe
// selects. Wraps any trigger via DialogTrigger asChild. Submitting is
// simulated; the M4 swap posts /checks instead.

"use client";

import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { PropertyChip } from "@/components/primitives/property-chip";
import { extractPropertiesFromText, getProducts } from "@/lib/data";

const NEW_PRODUCT = "__new__";

export function NewCheckModal({ children }: { children: React.ReactNode }) {
  const products = getProducts();
  const [open, setOpen] = useState(false);
  const [productId, setProductId] = useState<string>(products[0]?.id ?? "");
  const [newName, setNewName] = useState("");
  const [linksText, setLinksText] = useState("");
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const [depth, setDepth] = useState("2");
  const [pageCap, setPageCap] = useState("20");
  const [timeframe, setTimeframe] = useState("Feb 1 to Mar 31");
  const [submitting, setSubmitting] = useState(false);

  const chips = useMemo(
    () =>
      extractPropertiesFromText(linksText).filter(
        (c) => !removed.has(`${c.kind}:${c.label}`)
      ),
    [linksText, removed]
  );

  function reset() {
    setLinksText("");
    setRemoved(new Set());
    setNewName("");
    setSubmitting(false);
  }

  function startCheck() {
    setSubmitting(true);
    // Fixture mode: simulate run creation, then close. M4 posts /checks here.
    window.setTimeout(() => {
      setOpen(false);
      reset();
    }, 900);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) reset();
      }}
    >
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle className="text-base">New check</DialogTitle>
          <DialogDescription className="text-xs">
            Your global scorecard is applied automatically.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label className="text-[13px]">Product</Label>
            <Select value={productId} onValueChange={setProductId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Pick a product" />
              </SelectTrigger>
              <SelectContent>
                {products.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}{" "}
                    <span className="text-muted-foreground">
                      (existing product)
                    </span>
                  </SelectItem>
                ))}
                <SelectItem value={NEW_PRODUCT}>Create new product</SelectItem>
              </SelectContent>
            </Select>
            {productId === NEW_PRODUCT ? (
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Product name"
                className="mt-1"
              />
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-[13px]">Marketing properties</Label>
            <Textarea
              value={linksText}
              onChange={(e) => setLinksText(e.target.value)}
              placeholder="Paste links or describe the properties, e.g. check turbotax.intuit.com plus our socials facebook.com/turbotax and instagram.com/turbotax"
              className="min-h-[76px] text-[13px]"
            />
            {chips.length > 0 ? (
              <div className="mt-0.5 flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted-foreground">Detected</span>
                {chips.map((c) => (
                  <PropertyChip
                    key={`${c.kind}:${c.label}`}
                    kind={c.kind}
                    label={c.label}
                    onRemove={() =>
                      setRemoved(
                        (prev) => new Set(prev).add(`${c.kind}:${c.label}`)
                      )
                    }
                  />
                ))}
              </div>
            ) : null}
          </div>
          <div className="flex items-start gap-2.5">
            <div className="flex flex-1 flex-col gap-1.5">
              <Label className="text-xs text-muted-foreground">
                Crawl depth
              </Label>
              <Select value={depth} onValueChange={setDepth}>
                <SelectTrigger size="sm" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["1", "2", "3"].map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-1 flex-col gap-1.5">
              <Label className="text-xs text-muted-foreground">Page cap</Label>
              <Select value={pageCap} onValueChange={setPageCap}>
                <SelectTrigger size="sm" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["10", "20", "50"].map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-[1.4] flex-col gap-1.5">
              <Label className="text-xs text-muted-foreground">
                Posts from
              </Label>
              <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger size="sm" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["Feb 1 to Mar 31", "Last 30 days", "Last 90 days"].map(
                    (t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    )
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <DialogFooter className="border-t border-border pt-3">
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            onClick={startCheck}
            disabled={submitting || chips.length === 0}
          >
            {submitting ? <Loader2 className="size-3.5 animate-spin" /> : null}
            Start check
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
