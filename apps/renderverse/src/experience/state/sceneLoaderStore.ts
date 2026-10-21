import { create } from "zustand";

export type SceneLoaderAction =
  { type: "TOGGLE_ACTIVE" } | { type: "TOGGLE_INACTIVE" };

interface SceneLoaderState {
  isActive: boolean;
}

interface SceneLoaderStore extends SceneLoaderState {
  dispatch: (action: SceneLoaderAction) => void;
}

const reducer = (
  state: SceneLoaderState,
  action: SceneLoaderAction,
): SceneLoaderState => {
  switch (action.type) {
    case "TOGGLE_ACTIVE":
      return { isActive: true };
    case "TOGGLE_INACTIVE":
      return { isActive: false };
    default:
      return state;
  }
};

export const useSceneLoaderStore = create<SceneLoaderStore>((set) => ({
  isActive: false,
  dispatch: (action) => set((state) => reducer(state, action)),
}));
