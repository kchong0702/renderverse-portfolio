import { createContext, useContext, useReducer } from "react";
import PropTypes from "prop-types";

// 1. Create context
const SceneControlContext = createContext();

// 2. Create reducer
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

// 3. Create provider
const SceneControlProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, {
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
  });

  return (
    <SceneControlContext.Provider value={{ state, dispatch }}>
      {children}
    </SceneControlContext.Provider>
  );
};

// 4. Custom Hook
const useSceneControl = () => {
  const context = useContext(SceneControlContext);
  if (context === undefined)
    throw new Error(
      "SceneControlContext was used outside of the SceneControlProvider",
    );
  return context;
};

export { SceneControlProvider, useSceneControl };

// Props validation
SceneControlProvider.propTypes = {
  children: PropTypes.any,
};
