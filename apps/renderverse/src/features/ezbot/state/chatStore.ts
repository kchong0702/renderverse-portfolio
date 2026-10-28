import { create } from "zustand";

export type ChatAction =
  | { type: "OPEN" }
  | { type: "CLOSE" }
  | { type: "NAVIGATE" }
  | { type: "RESPONDING"; payload: boolean };

interface ChatState {
  isOpen: boolean;
  isResponding: boolean;
  returnToChat: boolean;
}

interface ChatStore extends ChatState {
  dispatch: (action: ChatAction) => void;
}

const reducer = (state: ChatState, action: ChatAction): ChatState => {
  switch (action.type) {
    case "OPEN":
      return { ...state, isOpen: true, returnToChat: false };
    case "CLOSE":
      return { ...state, isOpen: false };
    case "NAVIGATE":
      return { ...state, isOpen: false, returnToChat: true };
    case "RESPONDING":
      return { ...state, isResponding: action.payload };
    default:
      return state;
  }
};

export const useChatStore = create<ChatStore>((set) => ({
  isOpen: false,
  isResponding: false,
  returnToChat: false,
  dispatch: (action) => set((state) => reducer(state, action)),
}));
