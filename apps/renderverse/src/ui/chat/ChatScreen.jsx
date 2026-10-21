import styles from "./ChatScreen.module.css";
import { useSceneControl } from "../../hooks/useSceneControl";
import { useEffect, useCallback } from "react";
import Ezbot from "./Ezbot";
import Chat from "./Chat";
import { useChatControl, useOpenChat } from "../../hooks/useChatControl";
import { CONNECTION_STATUS, useEzbotStatus } from "../../hooks/useEzbotStatus";
import { useHotkey } from "../../hooks/useHotkey";

export default function ChatScreen() {
  const { dispatch } = useSceneControl();
  const { chatState, chatDispatch } = useChatControl();
  const openChat = useOpenChat();

  const { isOpen } = chatState;
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
