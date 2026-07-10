// meta: client-side disposition state for fixture mode (zustand). Holds the
// mutable lifecycle slice of each flag (state, team, note) seeded from
// fixtures; U6 rows and U7's Disposition panel both read and write it so a
// disposition made anywhere is visible everywhere. At M4 the actions become
// POST /flags/{id}/disposition calls and the store becomes the optimistic
// cache. Undo restores the seeded fixture state.

import { create } from "zustand";
import { flags } from "@/lib/fixtures";
import type { FlagState } from "@/lib/types";

export interface FlagLifecycle {
  state: FlagState;
  team: string | null;
  note: string | null;
}

interface FlagStore {
  lifecycles: Record<string, FlagLifecycle>;
  confirm: (flagId: string, team: string, note: string) => void;
  dismiss: (flagId: string, note?: string) => void;
  confirmAll: (flagIds: string[]) => void;
  dismissAll: (flagIds: string[]) => void;
  undo: (flagId: string) => void;
}

const seeded: Record<string, FlagLifecycle> = Object.fromEntries(
  flags.map((f) => [
    f.id,
    { state: f.state, team: f.assigned_team, note: f.note },
  ])
);

export const useFlagStore = create<FlagStore>((set) => ({
  lifecycles: { ...seeded },
  confirm: (flagId, team, note) =>
    set((s) => ({
      lifecycles: {
        ...s.lifecycles,
        [flagId]: {
          state: team ? "assigned" : "confirmed",
          team: team || null,
          note: note || null,
        },
      },
    })),
  dismiss: (flagId, note) =>
    set((s) => ({
      lifecycles: {
        ...s.lifecycles,
        [flagId]: { state: "dismissed", team: null, note: note ?? null },
      },
    })),
  confirmAll: (flagIds) =>
    set((s) => {
      const next = { ...s.lifecycles };
      for (const id of flagIds) {
        if (next[id]?.state === "open") {
          next[id] = { state: "confirmed", team: null, note: null };
        }
      }
      return { lifecycles: next };
    }),
  dismissAll: (flagIds) =>
    set((s) => {
      const next = { ...s.lifecycles };
      for (const id of flagIds) {
        if (next[id]?.state === "open") {
          next[id] = { state: "dismissed", team: null, note: null };
        }
      }
      return { lifecycles: next };
    }),
  undo: (flagId) =>
    set((s) => ({
      lifecycles: { ...s.lifecycles, [flagId]: { ...seeded[flagId] } },
    })),
}));
