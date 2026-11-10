import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { Outcome, RunEvent, Step } from "../api/assistant";

export type Part =
  | { kind: "thinking"; turn: string; text: string }
  | { kind: "text"; turn: string; text: string }
  | { kind: "step"; step: Step; substeps: Step[] };

export interface AssistantTurn {
  role: "assistant";
  taskId: string | null;
  parts: Part[];
  outcome: Outcome | null;
}

export type ChatEntry = { role: "user"; text: string } | AssistantTurn;

const upsert = (steps: Step[], step: Step) =>
  steps.some(({ id }) => id === step.id)
    ? steps.map((each) => (each.id === step.id ? step : each))
    : [...steps, step];

function applyEvent(turn: AssistantTurn, event: RunEvent): AssistantTurn {
  if (turn.outcome) return turn;
  switch (event.status) {
    case "started":
      return { ...turn, taskId: event.task_id };
    case "thinking":
    case "text": {
      const kind = event.status;
      const found = turn.parts.some(
        (part) => part.kind === kind && part.turn === event.turn,
      );
      return {
        ...turn,
        parts: found
          ? turn.parts.map((part) =>
              part.kind === kind && part.turn === event.turn
                ? { ...part, text: part.text + event.text }
                : part,
            )
          : [...turn.parts, { kind, turn: event.turn, text: event.text }],
      };
    }
    case "step": {
      const { step } = event;
      if (step.parent !== null)
        return {
          ...turn,
          parts: turn.parts.map((part) =>
            part.kind === "step" && part.step.id === step.parent
              ? { ...part, substeps: upsert(part.substeps, step) }
              : part,
          ),
        };
      return turn.parts.some(
        (part) => part.kind === "step" && part.step.id === step.id,
      )
        ? {
            ...turn,
            parts: turn.parts.map((part) =>
              part.kind === "step" && part.step.id === step.id
                ? { ...part, step }
                : part,
            ),
          }
        : {
            ...turn,
            parts: [...turn.parts, { kind: "step", step, substeps: [] }],
          };
    }
    case "completed": {
      const written = turn.parts.filter((part) => part.kind === "text").at(-1);
      return {
        ...turn,
        outcome: event,
        parts:
          !event.reply.trim() ||
          (written?.kind === "text" &&
            written.text.trim() === event.reply.trim())
            ? turn.parts
            : [
                ...turn.parts,
                { kind: "text", turn: "reply", text: event.reply },
              ],
      };
    }
    default:
      return { ...turn, outcome: event };
  }
}

interface AssistantState {
  open: boolean;
  setOpen: (open: boolean) => void;
  chatId: string;
  entries: ChatEntry[];
  add: (entry: ChatEntry) => void;
  apply: (event: RunEvent) => void;
  restore: (entries: ChatEntry[]) => void;
  newChat: () => void;
}

export const useAssistantStore = create<AssistantState>()(
  persist(
    (set) => ({
      open: false,
      setOpen: (open) => set({ open }),
      chatId: crypto.randomUUID(),
      entries: [],
      add: (entry) => set((state) => ({ entries: [...state.entries, entry] })),
      apply: (event) =>
        set(({ entries }) => {
          const last = entries.at(-1);
          return last?.role === "assistant"
            ? { entries: [...entries.slice(0, -1), applyEvent(last, event)] }
            : {};
        }),
      restore: (entries) => set({ entries }),
      newChat: () => set({ chatId: crypto.randomUUID(), entries: [] }),
    }),
    {
      name: "ops:assistant",
      version: 1,
      storage: createJSONStorage(() => sessionStorage),
      partialize: ({ chatId, entries }) => ({
        chatId,
        entries: entries.map((entry) =>
          entry.role === "assistant" && !entry.outcome
            ? { ...entry, outcome: { status: "cancelled" as const } }
            : entry,
        ),
      }),
    },
  ),
);
