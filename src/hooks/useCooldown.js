import { useSceneControl } from "./useSceneControl";
import { useEffect, useCallback } from "react";

export const useCooldown = () => {
  const { state, dispatch } = useSceneControl();

  const memoizedDispatch = useCallback(dispatch, [dispatch]);

  useEffect(() => {
    if (state.cooldown === true) {
      const cooldownTimer = setTimeout(() => {
        memoizedDispatch({ type: "COOLDOWN" });
      }, 1500);
      return () => clearTimeout(cooldownTimer);
    }
  }, [state.cooldown, memoizedDispatch]);
};
