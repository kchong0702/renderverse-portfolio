import { create } from "zustand";

interface AssistantState {
  open: boolean;
  setOpen: (open: boolean) => void;
}

// Kept outside the page so the panel stays open while the user moves between screens
export const useAssistantStore = create<AssistantState>()((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
}));
