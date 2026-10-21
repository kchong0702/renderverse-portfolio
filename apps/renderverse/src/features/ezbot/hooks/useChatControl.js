import { createContext, useCallback, useContext } from "react";
import { useSceneControl } from "@/experience/state/useSceneControl";
import { CONFIG } from "@/app/config";
import { useRecheckEzbot } from "./useEzbotStatus";

export const ChatControlContext = createContext();

export const useChatControl = () => {
  const context = useContext(ChatControlContext);
  if (context === undefined)
    throw new Error(
      "ChatControlContext was used outside of the ChatControlProvider",
    );
  return context;
};

export const useOpenChat = () => {
  const { state, dispatch } = useSceneControl();
  const { chatDispatch } = useChatControl();
  const recheckEzbot = useRecheckEzbot();

  const canOpen =
    CONFIG.isChatbotEnabled &&
    state.isLocked === true &&
    (state.specialIsLocked === true || state.specialIsLocked === null);

  return useCallback(() => {
    if (!canOpen) return;
    dispatch({ type: "SUNLOCK" });
    chatDispatch({ type: "OPEN" });
    recheckEzbot();
  }, [canOpen, dispatch, chatDispatch, recheckEzbot]);
};
