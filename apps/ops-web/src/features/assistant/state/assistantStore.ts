import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type {
  Changeset,
  Chat,
  Outcome,
  RunEvent,
  Step,
} from "../api/assistant";

export type Part =
  | { kind: "thinking"; turn: string; text: string }
  | { kind: "text"; turn: string; text: string }
  | { kind: "step"; step: Step; substeps: Step[] }
  | { kind: "changeset"; changeset: Changeset };

export interface AssistantTurn {
  role: "assistant";
  taskId: string | null;
  lastEventId: string | null;
  parts: Part[];
  outcome: Outcome | null;
  startedAt: number;
  endedAt: number | null;
  reconnecting: number;
}

export type ChatEntry =
  { role: "user"; text: string; answered?: boolean } | AssistantTurn;

const upsert = (steps: Step[], step: Step) =>
  steps.some(({ id }) => id === step.id)
    ? steps.map((each) => (each.id === step.id ? step : each))
    : [...steps, step];

function applyEvent(turn: AssistantTurn, event: RunEvent): AssistantTurn {
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
    case "changeset":
      return {
        ...turn,
        parts: [...turn.parts, { kind: "changeset", changeset: event }],
      };
    case "completed": {
      const written = turn.parts.filter((part) => part.kind === "text").at(-1);
      return {
        ...turn,
        outcome: event,
        endedAt: Date.now(),
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
      return { ...turn, outcome: event, endedAt: Date.now() };
  }
}

export interface ShownDocument {
  id: string;
  title: string;
}

type Chats = Record<Chat["kind"], Partial<Record<string, ChatEntry[]>>>;

interface AssistantState {
  open: boolean;
  setOpen: (open: boolean) => void;
  chatId: string;
  document: ShownDocument | null;
  setDocument: (document: ShownDocument | null) => void;
  chats: Chats;
  add: (chat: Chat, entry: ChatEntry) => void;
  apply: (chat: Chat, event: RunEvent, id?: string) => void;
  reconnect: (chat: Chat, attempt: number) => void;
  restore: (chat: Chat, entries: ChatEntry[]) => void;
  newChat: (chat: Chat) => void;
  reset: () => void;
}

const withEntries = (
  chats: Chats,
  { kind, id }: Chat,
  update: (entries: ChatEntry[]) => ChatEntry[],
): Chats => ({
  ...chats,
  [kind]: { ...chats[kind], [id]: update(chats[kind][id] ?? []) },
});

export const openTurn = (entries: ChatEntry[]) => {
  const last = entries.at(-1);
  return last?.role === "assistant" && !last.outcome ? last : undefined;
};

export const useAssistantStore = create<AssistantState>()(
  persist(
    (set) => ({
      open: false,
      setOpen: (open) => set({ open }),
      chatId: crypto.randomUUID(),
      document: null,
      setDocument: (document) => set({ document }),
      chats: { assistant: {}, document: {} },
      add: (chat, entry) =>
        set(({ chats }) => ({
          chats: withEntries(chats, chat, (entries) => [...entries, entry]),
        })),
      apply: (chat, event, id) =>
        set(({ chats }) => ({
          chats: withEntries(chats, chat, (entries) => {
            const last = openTurn(entries);
            return last
              ? [
                  ...entries.slice(0, -1),
                  {
                    ...applyEvent(last, event),
                    lastEventId: id ?? last.lastEventId,
                    reconnecting: 0,
                  },
                ]
              : entries;
          }),
        })),
      reconnect: (chat, attempt) =>
        set(({ chats }) => ({
          chats: withEntries(chats, chat, (entries) => {
            const last = openTurn(entries);
            return last
              ? [...entries.slice(0, -1), { ...last, reconnecting: attempt }]
              : entries;
          }),
        })),
      restore: (chat, entries) =>
        set(({ chats }) => ({
          chats: withEntries(chats, chat, () => entries),
        })),
      newChat: (chat) =>
        set(({ chats }) =>
          chat.kind === "assistant"
            ? {
                chatId: crypto.randomUUID(),
                chats: { ...chats, assistant: {} },
              }
            : { chats: withEntries(chats, chat, () => []) },
        ),
      reset: () =>
        set({
          open: false,
          chatId: crypto.randomUUID(),
          document: null,
          chats: { assistant: {}, document: {} },
        }),
    }),
    {
      name: "ops:assistant",
      version: 3,
      storage: createJSONStorage(() => sessionStorage),
      partialize: ({ chatId, chats }) => ({ chatId, chats }),
    },
  ),
);
