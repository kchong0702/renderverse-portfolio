import styles from "./ChatScreen.module.css";
import { useSceneStore } from "@/experience/state/sceneStore";
import { useEffect, useCallback } from "react";
import Ezbot from "./Ezbot";
import Chat from "./Chat";
import { useChatStore } from "@/features/ezbot/state/chatStore";
import { useOpenChat } from "@/features/ezbot/hooks/useOpenChat";
import {
  CONNECTION_STATUS,
  useEzbotStatus,
} from "@/features/ezbot/hooks/useEzbotStatus";
import { useHotkey } from "@/shared/hooks/useHotkey";

export default function ChatScreen() {
  const dispatch = useSceneStore((s) => s.dispatch);
  const isOpen = useChatStore((s) => s.isOpen);
  const chatDispatch = useChatStore((s) => s.dispatch);
  const openChat = useOpenChat();
  const connectionStatus = useEzbotStatus();

  const hide = () => {
    dispatch({ type: "SLOCK" });
    chatDispatch({ type: "CLOSE" });
  };

  const setReplying = useCallback(
    (isReplying) => chatDispatch({ type: "REPLYING", payload: isReplying }),
    [chatDispatch],
  );

  useHotkey("KeyC", openChat);

  useEffect(() => {
    if (isOpen) {
      document.getElementById("chat-overlay").style.display = "flex";
    } else {
      document.getElementById("chat-overlay").style.display = "none";
    }
  }, [isOpen]);

  return (
    <div id="chat-overlay" className={styles.chatOverlay}>
      <Ezbot
        isActive={connectionStatus === CONNECTION_STATUS.ONLINE}
        isLightOff={false}
      />
      <Chat
        close={hide}
        isOpen={isOpen}
        connectionStatus={connectionStatus}
        setReplying={setReplying}
      />
    </div>
  );
}
