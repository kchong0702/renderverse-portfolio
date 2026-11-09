import { create } from "zustand";

export interface ModalData {
  id: string;
  content?: unknown;
}

export type ModalAction =
  { type: "TOGGLE_OPEN"; payload?: ModalData } | { type: "TOGGLE_CLOSE" };

export type ModalInteraction = (
  type: ModalAction["type"],
  payload?: ModalData,
) => void;

interface ModalState {
  isShow: boolean;
  data: ModalData | null;
}

interface ModalStore extends ModalState {
  dispatch: (action: ModalAction) => void;
}

const reducer = (state: ModalState, action: ModalAction): ModalState => {
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

export const useModalStore = create<ModalStore>((set) => ({
  isShow: false,
  data: null,
  dispatch: (action) => set((state) => reducer(state, action)),
}));
