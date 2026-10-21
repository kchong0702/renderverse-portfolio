import { create } from "zustand";

const reducer = (state, action) => {
  switch (action.type) {
    case "TOGGLE_OPEN":
      return {
        isShow: true,
        data: action.payload ? action.payload : null,
      };
    case "TOGGLE_CLOSE":
      return { isShow: false, data: null };
    default:
      return state;
  }
};

export const useModalStore = create((set) => ({
  isShow: false,
  data: null,
  dispatch: (action) => set((state) => reducer(state, action)),
}));
