// meta: paste-content dialog for a live run parked in awaiting_input (07 §2
// barrier). Lists each parked property with a textarea + Paste content + Skip,
// calling POST /runs/{id}/paste-content and /runs/{id}/skip-property. The
// parked list is driven by polled product data, so as each property resolves
// it drops off; when the run resumes and completes the card flips on the next
// poll. No layout change to existing surfaces; this is a self-contained Dialog.

"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { PropertyIcon } from "@/components/primitives/property-chip";
import { useResolveProperty } from "@/lib/data";
import type { ParkedProperty } from "@/lib/fixtures";

export function PasteDialog({
  productId,
  runId,
  parked,
}: {
  productId: string;
  runId: string;
  parked: ParkedProperty[];
}) {
  const [open, setOpen] = useState(false);
  const [texts, setTexts] = useState<Record<string, string>>({});
  const { paste, skip } = useResolveProperty(productId, runId);
  const pending = paste.isPending || skip.isPending;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          Provide content
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle className="text-base">Provide content</DialogTitle>
          <DialogDescription className="text-xs">
            These mediums could not be fetched automatically. Paste the
            content to include each one, or skip it and note the gap.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          {parked.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              All mediums resolved. The run is finishing.
            </p>
          ) : (
            parked.map((p) => (
              <div key={p.id} className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <PropertyIcon
                    kind={p.kind}
                    className="size-3.5 text-muted-foreground"
                  />
                  <span className="text-[13px] font-medium">{p.label}</span>
                </div>
                <Textarea
                  aria-label={`Content for ${p.label}`}
                  value={texts[p.id] ?? ""}
                  onChange={(e) =>
                    setTexts((t) => ({ ...t, [p.id]: e.target.value }))
                  }
                  placeholder="Paste the post or page content"
                  className="min-h-[64px] text-[13px]"
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    disabled={pending || !(texts[p.id] ?? "").trim()}
                    onClick={() =>
                      paste.mutate({
                        property_id: p.id,
                        text: texts[p.id] ?? "",
                      })
                    }
                  >
                    {paste.isPending ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : null}
                    Paste content
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={pending}
                    onClick={() => skip.mutate({ property_id: p.id })}
                  >
                    Skip
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
