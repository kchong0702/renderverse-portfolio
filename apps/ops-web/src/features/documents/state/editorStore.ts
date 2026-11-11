import type { Align } from "@renderverse/document-renderer";
import type { Editor } from "@tiptap/core";
import { create } from "zustand";

export type Panel = "design" | "entry" | "assistant";

type Hovered = "block" | "entry" | "bullet";

export interface Drag {
  kind: "k" | "e" | "b";
  id: string;
}

interface Formatting {
  editor: Editor;
  path: string;
  commit: (align?: Align) => void;
}

interface Initial {
  panel: Panel;
  details: string | null;
  selected: string | null;
  hovered: Record<Hovered, string | null>;
  inserting: string | null;
  moving: string | null;
  drag: Drag | null;
  dropKey: string | null;
  focus: string | null;
  formatting: Formatting | null;
  toolbar: { left: number; top: number } | null;
}

interface EditorState extends Initial {
  showPanel: (panel: Panel) => void;
  openDetails: (entry: string) => void;
  closeDetails: () => void;
  select: (key: string) => void;
  clearSelection: () => void;
  enter: (hovered: Hovered, id: string) => void;
  leave: (hovered: Hovered, id: string) => void;
  toggleInserting: (block: string) => void;
  toggleMoving: (block: string) => void;
  startDrag: (drag: Drag) => void;
  dropOver: (key: string) => void;
  endDrag: () => void;
  focusNext: (path: string | null) => void;
  setFormatting: (formatting: Formatting | null) => void;
  setToolbar: (toolbar: { left: number; top: number } | null) => void;
  reset: () => void;
}

const HOVER_MS = { block: 400, entry: 400, bullet: 0 };

const initial: Initial = {
  panel: "design",
  details: null,
  selected: null,
  hovered: { block: null, entry: null, bullet: null },
  inserting: null,
  moving: null,
  drag: null,
  dropKey: null,
  focus: null,
  formatting: null,
  toolbar: null,
};

const leaving: Partial<Record<Hovered, ReturnType<typeof setTimeout>>> = {};

export const useEditorStore = create<EditorState>()((set) => ({
  ...initial,
  showPanel: (panel) => set({ panel }),
  openDetails: (details) => set({ details, panel: "entry" }),
  closeDetails: () => set({ details: null, panel: "design" }),
  select: (key) =>
    set((state) => ({
      selected: state.selected === key ? null : key,
      inserting: null,
      moving: null,
    })),
  clearSelection: () => set({ selected: null, moving: null }),
  enter: (hovered, id) => {
    clearTimeout(leaving[hovered]);
    set((state) => ({ hovered: { ...state.hovered, [hovered]: id } }));
  },
  leave: (hovered, id) => {
    leaving[hovered] = setTimeout(
      () =>
        set((state) =>
          state.hovered[hovered] === id
            ? {
                hovered: { ...state.hovered, [hovered]: null },
                inserting: state.inserting === id ? null : state.inserting,
              }
            : {},
        ),
      HOVER_MS[hovered],
    );
  },
  toggleInserting: (block) =>
    set((state) => ({
      inserting: state.inserting === block ? null : block,
    })),
  toggleMoving: (block) =>
    set((state) => ({ moving: state.moving === block ? null : block })),
  startDrag: (drag) =>
    set({ drag, selected: null, inserting: null, moving: null }),
  dropOver: (dropKey) => set({ dropKey }),
  endDrag: () => set({ drag: null, dropKey: null }),
  focusNext: (focus) => set({ focus }),
  setFormatting: (formatting) => set({ formatting }),
  setToolbar: (toolbar) => set({ toolbar }),
  reset: () =>
    set((state) => ({
      ...initial,
      panel: state.panel === "entry" ? "design" : state.panel,
    })),
}));
