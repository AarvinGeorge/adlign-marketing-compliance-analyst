// meta: U3 New check modal (client Dialog, not a route). Product create-or-pick
// (list via useProducts, all API-backed), freeform links textarea with detected
// medium chips (deterministic client-side extraction), and a single
// "Pages per medium" cap (semantic discovery top-N; crawl depth and post
// timeframe are gone with the ingestion redesign). Submit runs a LIVE check:
// create-new POSTs /products with the chips as mediums then POSTs /checks
// {mode: live, page_cap}; existing product POSTs /checks {mode: live,
// page_cap}. On success the modal closes and product queries invalidate.
// Display vocabulary: "marketing mediums" (code identifiers keep property_*).

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
import {
  chipsToProperties,
  extractPropertiesFromText,
  useCreateProductAndCheck,
  useProducts,
  useStartCheck,
} from "@/lib/data";

const NEW_PRODUCT = "__new__";

export function NewCheckModal({ children }: { children: React.ReactNode }) {
  const { products } = useProducts();
  const startCheckMutation = useStartCheck();
  const createAndCheck = useCreateProductAndCheck();
  const [open, setOpen] = useState(false);
  const [productId, setProductId] = useState<string>("");
  const [newName, setNewName] = useState("");
  const [linksText, setLinksText] = useState("");
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const [pageCap, setPageCap] = useState("20");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const selectedId = productId || products[0]?.id || "";
  const isNew = selectedId === NEW_PRODUCT;

  const chips = useMemo(
    () =>
      extractPropertiesFromText(linksText).filter(
        (c) => !removed.has(`${c.kind}:${c.label}`)
      ),
    [linksText, removed]
  );

  const canSubmit = isNew
    ? newName.trim().length > 0 && chips.length > 0
    : Boolean(selectedId);

  function reset() {
    setLinksText("");
    setRemoved(new Set());
    setNewName("");
    setSubmitting(false);
    setSubmitError(null);
  }

  function done() {
    setOpen(false);
    reset();
  }
  function fail(err: unknown) {
    setSubmitting(false);
    setSubmitError(err instanceof Error ? err.message : "The check could not start.");
  }

  function startCheck() {
    setSubmitting(true);
    setSubmitError(null);
    const cap = Number(pageCap);
    if (isNew) {
      createAndCheck.mutate(
        {
          name: newName.trim(),
          properties: chipsToProperties(chips),
          pageCap: cap,
        },
        { onSuccess: done, onError: fail }
      );
      return;
    }
    startCheckMutation.mutate(
      { productId: selectedId, pageCap: cap },
      { onSuccess: done, onError: fail }
    );
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
            <Select value={selectedId} onValueChange={setProductId}>
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
            {isNew ? (
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Product name"
                className="mt-1"
              />
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-[13px]">Marketing mediums</Label>
            <Textarea
              value={linksText}
              onChange={(e) => setLinksText(e.target.value)}
              placeholder="Paste links or describe the mediums, e.g. check turbotax.intuit.com plus our socials facebook.com/turbotax and instagram.com/turbotax"
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
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-muted-foreground">
              Pages per medium
            </Label>
            <Select value={pageCap} onValueChange={setPageCap}>
              <SelectTrigger size="sm" className="w-[130px]">
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
            <p className="text-xs text-muted-foreground">
              The most rule-relevant pages, found by semantic search against
              your scorecard.
            </p>
          </div>
        </div>
        <DialogFooter className="border-t border-border pt-3">
          {submitError ? (
            <span className="mr-auto self-center text-xs font-medium text-danger-text">
              {submitError}
            </span>
          ) : null}
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button onClick={startCheck} disabled={submitting || !canSubmit}>
            {submitting ? <Loader2 className="size-3.5 animate-spin" /> : null}
            Start check
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
