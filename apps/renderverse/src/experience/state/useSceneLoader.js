import { createContext, useContext } from "react";

export const SceneLoaderContext = createContext();

export const useSceneLoader = () => {
  const context = useContext(SceneLoaderContext);
  if (context === undefined)
    throw new Error(
      "SceneLoaderContext was used outside of the SceneLoaderProvider",
    );
  return context;
};
