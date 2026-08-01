import { createContext, useContext, useReducer } from "react";
import PropTypes from "prop-types";

// 1. Create context
const SceneLoaderContext = createContext();

// 2. Create reducer
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

// 3. Create provider
const SceneLoaderProvider = ({ children }) => {
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
};

// 4. Custom Hook
const useSceneLoader = () => {
  const context = useContext(SceneLoaderContext);
  if (context === undefined)
    throw new Error(
      "SceneLoaderContext was used outside of the SceneLoaderProvider",
    );
  return context;
};

export { SceneLoaderProvider, useSceneLoader };

// Props validation
SceneLoaderProvider.propTypes = {
  children: PropTypes.any,
};
