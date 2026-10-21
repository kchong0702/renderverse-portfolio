import { createContext, useContext } from "react";

export const SceneControlContext = createContext();

export const useSceneControl = () => {
  const context = useContext(SceneControlContext);
  if (context === undefined)
    throw new Error(
      "SceneControlContext was used outside of the SceneControlProvider",
    );
  return context;
};
