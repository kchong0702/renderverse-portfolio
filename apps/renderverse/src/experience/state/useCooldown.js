import { useEffect } from "react";
import { useSceneStore } from "./sceneStore";

export const useCooldown = () => {
  const cooldown = useSceneStore((s) => s.cooldown);
  const dispatch = useSceneStore((s) => s.dispatch);

  useEffect(() => {
    if (cooldown === true) {
      const cooldownTimer = setTimeout(() => {
        dispatch({ type: "COOLDOWN" });
      }, 1500);
      return () => clearTimeout(cooldownTimer);
    }
  }, [cooldown, dispatch]);
};
