import { create } from "zustand";
import type { Outcome, RunEvent, Step, ThreadMessage } from "../api/assistant";

export type Part =
  | { kind: "thinking"; turn: string; text: string }
  | { kind: "text"; turn: string; text: string }
  | { kind: "step"; step: Step; substeps: Step[] }
  | {
      kind: "proposed";
      documentId: string;
      changesetId: string;
      createdAt: string;
    }
  | { kind: "saved"; saved: number };

export type Connection =
  | { status: "connected" }
  | { status: "reconnecting"; attempt: number }
  | { status: "retrying"; attempt: number };

export interface AssistantTurn {
  role: "assistant";
  id: string;
  taskId: string | null;
  parts: Part[];
  outcome: Outcome | null;
  startedAt: number | null;
  endedAt: number | null;
  connection: Connection;
}

export type ChatEntry =
  | {
      role: "user";
      id: string;
      text: string;
      answered?: boolean;
      decision?: "approve" | "reject";
    }
  | AssistantTurn;

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
        parts: [
          ...turn.parts,
          {
            kind: "proposed",
            documentId: event.document_id,
            changesetId: event.changeset_id,
            createdAt: event.created_at,
          },
        ],
      };
    case "profile_saved":
      return {
        ...turn,
        parts: [...turn.parts, { kind: "saved", saved: event.saved }],
      };
    case "reconnecting":
      return {
        ...turn,
        connection: { status: "retrying", attempt: event.attempt },
      };
    case "reconnected":
      return { ...turn, connection: { status: "connected" } };
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

export function historyEntry(message: ThreadMessage): ChatEntry {
  if (message.role === "user")
    return {
      role: "user",
      id: message.id,
      text: message.text,
    };
  const events: RunEvent[] = [
    ...(message.steps ?? []).map((step) => ({ status: "step" as const, step })),
    ...(message.failure === null
      ? [{ status: "completed" as const, reply: message.text }]
      : [
          ...(message.text
            ? [{ status: "text" as const, turn: "reply", text: message.text }]
            : []),
          { status: "failed" as const, reason: message.failure },
        ]),
  ];
  const turn = events.reduce<AssistantTurn>(applyEvent, {
    role: "assistant",
    id: message.id,
    taskId: null,
    parts: [],
    outcome: null,
    startedAt: null,
    endedAt: null,
    connection: { status: "connected" },
  });
  return {
    ...turn,
    parts: [
      ...turn.parts,
      ...message.changesets.map((changeset) => ({
        kind: "proposed" as const,
        documentId: changeset.document_id,
        changesetId: changeset.id,
        createdAt: changeset.created_at,
      })),
    ],
  };
}

export interface ShownDocument {
  id: string;
  title: string;
}

type Live = Partial<Record<string, ChatEntry[]>>;

interface AssistantState {
  open: boolean;
  setOpen: (open: boolean) => void;
  document: ShownDocument | null;
  setDocument: (document: ShownDocument | null) => void;
  live: Live;
  add: (threadId: string, entry: ChatEntry) => void;
  apply: (threadId: string, event: RunEvent) => void;
  reconnect: (threadId: string, attempt: number) => void;
  restore: (threadId: string, entries: ChatEntry[]) => void;
}

const withEntries = (
  live: Live,
  threadId: string,
  update: (entries: ChatEntry[]) => ChatEntry[],
): Live => ({ ...live, [threadId]: update(live[threadId] ?? []) });

export const openTurn = (entries: ChatEntry[]) => {
  const last = entries.at(-1);
  return last?.role === "assistant" && !last.outcome ? last : undefined;
};

const withOpenTurn = (
  live: Live,
  threadId: string,
  update: (turn: AssistantTurn) => AssistantTurn,
): Live =>
  withEntries(live, threadId, (entries) => {
    const last = openTurn(entries);
    return last ? [...entries.slice(0, -1), update(last)] : entries;
  });

export const useAssistantStore = create<AssistantState>()((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
  document: null,
  setDocument: (document) => set({ document }),
  live: {},
  add: (threadId, entry) =>
    set(({ live }) => ({
      live: withEntries(live, threadId, (entries) => [...entries, entry]),
    })),
  apply: (threadId, event) =>
    set(({ live }) => ({
      live: withOpenTurn(live, threadId, (turn) =>
        applyEvent({ ...turn, connection: { status: "connected" } }, event),
      ),
    })),
  reconnect: (threadId, attempt) =>
    set(({ live }) => ({
      live: withOpenTurn(live, threadId, (turn) => ({
        ...turn,
        connection: { status: "reconnecting", attempt },
      })),
    })),
  restore: (threadId, entries) =>
    set(({ live }) => ({
      live: withEntries(live, threadId, () => entries),
    })),
}));
