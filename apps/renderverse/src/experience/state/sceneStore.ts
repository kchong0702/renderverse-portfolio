import { create } from "zustand";

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface CameraFocus {
  look: Vec3;
  pos: Vec3;
  showBack?: boolean;
}

export interface AroundAnimation {
  focus: Vec3;
  radius: number;
}

export interface SceneState {
  isLocked: boolean;
  specialIsLocked: boolean | null;
  showCrosshair: boolean;
  cooldown: boolean;
  focus: CameraFocus | null;
  isTLocked: boolean;
  tFocus: [number, number, number] | null;
  tInnerFocus: boolean;
  tInnerLight: boolean;
  tInnerZoom: number;
  tInnerAround: AroundAnimation | null;
}

export type SceneAction =
  | { type: "LOCK" }
  | { type: "UNLOCK" }
  | { type: "SLOCK" }
  | { type: "SUNLOCK"; payload?: CameraFocus }
  | { type: "COOLDOWN" }
  | { type: "TLOCK" }
  | { type: "TUNLOCK" }
  | { type: "TFOCUS"; payload?: [number, number, number] }
  | { type: "TINNERFOCUS"; payload?: CameraFocus }
  | { type: "TINNERLIGHT" }
  | { type: "TINNERZOOM"; payload?: number }
  | { type: "TINNERZOOMOUT" }
  | { type: "TINNERAROUND"; payload?: AroundAnimation };

export type SceneActionType = SceneAction["type"];

export type SceneActionPayload<T extends SceneActionType> =
  Extract<SceneAction, { type: T }> extends { payload?: infer P } ? P : never;

export type SceneInteraction = <T extends SceneActionType>(
  type: T,
  payload?: SceneActionPayload<T>,
) => void;

interface SceneStore extends SceneState {
  dispatch: (action: SceneAction) => void;
}

const reducer = (state: SceneState, action: SceneAction): SceneState => {
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

export const useSceneStore = create<SceneStore>((set) => ({
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
