import { useCallback } from "react";
import { useSceneStore } from "@/experience/state/sceneStore";
import { useChatStore } from "../state/chatStore";

export const useBackToChat = () => {
  const dispatch = useSceneStore((s) => s.dispatch);
  const chatDispatch = useChatStore((s) => s.dispatch);

  return useCallback(() => {
    if (!useChatStore.getState().returnToChat) {
      dispatch({ type: "SLOCK" });
      return;
    }
    dispatch({ type: "SUNLOCK" });
    chatDispatch({ type: "OPEN" });
  }, [dispatch, chatDispatch]);
};
