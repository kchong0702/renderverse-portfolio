import { create } from "zustand";

export type ChatAction =
  { type: "OPEN" } | { type: "CLOSE" } | { type: "REPLYING"; payload: boolean };

interface ChatState {
  isOpen: boolean;
  isReplying: boolean;
}

interface ChatStore extends ChatState {
  dispatch: (action: ChatAction) => void;
}

const reducer = (state: ChatState, action: ChatAction): ChatState => {
  switch (action.type) {
    case "OPEN":
      return { ...state, isOpen: true };
    case "CLOSE":
      return { ...state, isOpen: false };
    case "REPLYING":
      return { ...state, isReplying: action.payload };
    default:
      return state;
  }
};

export const useChatStore = create<ChatStore>((set) => ({
  isOpen: false,
  isReplying: false,
  dispatch: (action) => set((state) => reducer(state, action)),
}));
