import { create } from "zustand";

const reducer = (state, action) => {
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

export const useChatStore = create((set) => ({
  isOpen: false,
  isReplying: false,
  dispatch: (action) => set((state) => reducer(state, action)),
}));
