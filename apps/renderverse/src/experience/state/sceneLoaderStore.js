import { create } from "zustand";

const reducer = (state, action) => {
  switch (action.type) {
    case "TOGGLE_ACTIVE":
      return { isActive: true };
    case "TOGGLE_INACTIVE":
      return { isActive: false };
    default:
      return state;
  }
};

export const useSceneLoaderStore = create((set) => ({
  isActive: false,
  dispatch: (action) => set((state) => reducer(state, action)),
}));
