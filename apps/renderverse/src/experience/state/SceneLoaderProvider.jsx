import { useReducer } from "react";
import PropTypes from "prop-types";
import { SceneLoaderContext } from "./useSceneLoader";

const reducer = (state, action) => {
  switch (action.type) {
    case "TOGGLE_ACTIVE":
      return {
        isActive: true,
      };
    case "TOGGLE_INACTIVE":
      return {
        isActive: false,
      };
    default:
      return state;
  }
};

export default function SceneLoaderProvider({ children }) {
  const [sceneLoaderState, dispatchSceneLoader] = useReducer(reducer, {
    isActive: false,
  });

  return (
    <SceneLoaderContext.Provider
      value={{ sceneLoaderState, dispatchSceneLoader }}
    >
      {children}
    </SceneLoaderContext.Provider>
  );
}

SceneLoaderProvider.propTypes = {
  children: PropTypes.any,
};
