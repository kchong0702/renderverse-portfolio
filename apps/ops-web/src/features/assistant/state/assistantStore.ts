import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { AssistantReply } from "../api/assistant";

export type ChatEntry =
  { role: "user"; text: string } | { role: "assistant"; reply: AssistantReply };

interface AssistantState {
  open: boolean;
  setOpen: (open: boolean) => void;
  entries: ChatEntry[];
  add: (entry: ChatEntry) => void;
  restore: (entries: ChatEntry[]) => void;
}

export const useAssistantStore = create<AssistantState>()(
  persist(
    (set) => ({
      open: false,
      setOpen: (open) => set({ open }),
      entries: [],
      add: (entry) => set((state) => ({ entries: [...state.entries, entry] })),
      restore: (entries) => set({ entries }),
    }),
    {
      name: "ops:assistant",
      storage: createJSONStorage(() => sessionStorage),
      partialize: ({ entries }) => ({ entries }),
    },
  ),
);
