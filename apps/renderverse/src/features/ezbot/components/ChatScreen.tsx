import styles from "./ChatScreen.module.css";
import { useSceneStore } from "@/experience/state/sceneStore";
import { useEffect } from "react";
import Ezbot from "./Ezbot";
import Chat from "./Chat";
import { useChatStore } from "@/features/ezbot/state/chatStore";
import { useOpenChat } from "@/features/ezbot/hooks/useOpenChat";
import {
  CONNECTION_STATUS,
  useEzbotStatus,
} from "@/features/ezbot/hooks/useEzbotSession";
import { useHotkey } from "@/shared/hooks/useHotkey";
import { useMediaQuery } from "@/shared/hooks/useMediaQuery";

export default function ChatScreen() {
  const dispatch = useSceneStore((s) => s.dispatch);
  const isOpen = useChatStore((s) => s.isOpen);
  const chatDispatch = useChatStore((s) => s.dispatch);
  const openChat = useOpenChat();
  const connectionStatus = useEzbotStatus();
  const isNarrow = useMediaQuery("(max-width: 900px)");

  const hide = () => {
    dispatch({ type: "SLOCK" });
    chatDispatch({ type: "CLOSE" });
  };

  useHotkey("KeyC", openChat);

  useEffect(() => {
    const overlay = document.getElementById("chat-overlay");
    if (!overlay) return;
    if (isOpen) {
      overlay.style.display = "flex";
    } else {
      overlay.style.display = "none";
    }
  }, [isOpen]);

  return (
    <div id="chat-overlay" className={styles.chatOverlay}>
      {!isNarrow && (
        <Ezbot
          isActive={connectionStatus === CONNECTION_STATUS.ONLINE}
          isLightOff={false}
        />
      )}
      <Chat close={hide} isOpen={isOpen} connectionStatus={connectionStatus} />
    </div>
  );
}
