import { useCallback } from "react";
import { useSceneStore } from "@/experience/state/sceneStore";
import { CONFIG } from "@/app/config";
import { useChatStore } from "../state/chatStore";
import { useRecheckEzbot } from "./useEzbotStatus";

export const useOpenChat = () => {
  const isLocked = useSceneStore((s) => s.isLocked);
  const specialIsLocked = useSceneStore((s) => s.specialIsLocked);
  const dispatch = useSceneStore((s) => s.dispatch);
  const chatDispatch = useChatStore((s) => s.dispatch);
  const recheckEzbot = useRecheckEzbot();

  const canOpen =
    CONFIG.isChatbotEnabled &&
    isLocked === true &&
    (specialIsLocked === true || specialIsLocked === null);

  return useCallback(() => {
    if (!canOpen) return;
    dispatch({ type: "SUNLOCK" });
    chatDispatch({ type: "OPEN" });
    recheckEzbot();
  }, [canOpen, dispatch, chatDispatch, recheckEzbot]);
};
