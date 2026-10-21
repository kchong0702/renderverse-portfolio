import { create } from "zustand";

const reducer = (state, action) => {
  switch (action.type) {
    case "LOCK":
      return {
        ...state,
        isLocked: true,
        showCrosshair: true,
        cooldown: true,
        focus: null,
      };
    case "UNLOCK":
      return {
        ...state,
        isLocked: false,
        showCrosshair: false,
        cooldown: true,
        focus: null,
      };
    case "SLOCK":
      return {
        ...state,
        specialIsLocked: true,
        showCrosshair: true,
        cooldown: true,
        focus: null,
      };
    case "SUNLOCK":
      return {
        ...state,
        specialIsLocked: false,
        showCrosshair: false,
        cooldown: true,
        focus: action.payload ? action.payload : null,
      };
    case "COOLDOWN":
      return { ...state, cooldown: false };
    // Figurine Room
    case "TLOCK":
      return {
        ...state,
        isTLocked: true,
        specialIsLocked: false,
        showCrosshair: false,
      };
    case "TUNLOCK":
      return {
        ...state,
        isTLocked: false,
        specialIsLocked: true,
        showCrosshair: true,
      };
    case "TFOCUS":
      return { ...state, tFocus: action.payload ? action.payload : null };
    case "TINNERFOCUS":
      return {
        ...state,
        tInnerFocus: !state.tInnerFocus,
        focus: action.payload ? action.payload : null,
      };
    case "TINNERLIGHT":
      return { ...state, tInnerLight: !state.tInnerLight };
    case "TINNERZOOM":
      return { ...state, tInnerZoom: action.payload ? action.payload : 1 };
    case "TINNERZOOMOUT":
      return { ...state, tInnerZoom: 1 };
    case "TINNERAROUND":
      return {
        ...state,
        tInnerAround: action.payload ? action.payload : null,
      };
    default:
      return state;
  }
};

export const useSceneStore = create((set) => ({
  isLocked: false,
  specialIsLocked: null,
  showCrosshair: false,
  cooldown: false,
  focus: null,
  isTLocked: false,
  tFocus: null,
  tInnerFocus: false,
  tInnerLight: true,
  tInnerZoom: 1,
  tInnerAround: null,
  dispatch: (action) => set((state) => reducer(state, action)),
}));
