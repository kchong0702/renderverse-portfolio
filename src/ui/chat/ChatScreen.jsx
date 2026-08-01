import styles from "./ChatScreen.module.css";
import { useSceneControl } from "../../hooks/useSceneControl";
import { useEffect, useCallback, useState } from "react";
import Ezbot from "./Ezbot";
import Chat from "./Chat";
import { useChatControl } from "../../hooks/useChatControl";

export default function ChatScreen() {
  const { state, dispatch } = useSceneControl();
  const { chatDispatch } = useChatControl();

  const memoizedDispatch = useCallback(dispatch, [dispatch]);
  const memoizedChatDispatch = useCallback(chatDispatch, [chatDispatch]);

  const [isShow, setShow] = useState(false);
  const [isConnectionActive, setConnectionActive] = useState(false);

  const hide = () => {
    setShow(false);
    memoizedDispatch({ type: "SLOCK" });
    memoizedChatDispatch({ type: "CLOSE" });
  };

  useEffect(() => {
    const handleChat = (e) => {
      if (
        (e.key === "c" || e.code === 67) &&
        state.isLocked === true &&
        (state.specialIsLocked === true || state.specialIsLocked === null)
      ) {
        setShow(true);
        memoizedDispatch({ type: "SUNLOCK" });
        memoizedChatDispatch({ type: "OPEN" });
      }
    };

    document.addEventListener("keydown", handleChat);

    return () => {
      document.removeEventListener("keydown", handleChat);
    };
  }, [
    memoizedChatDispatch,
    memoizedDispatch,
    state.isLocked,
    state.menuState,
    state.specialIsLocked,
  ]);

  useEffect(() => {
    if (isShow) {
      document.getElementById("chat-overlay").style.display = "flex";
    } else {
      document.getElementById("chat-overlay").style.display = "none";
    }
  }, [isShow]);

  return (
    <div id="chat-overlay" className={styles.chatOverlay}>
      <Ezbot isActive={isConnectionActive} isLightOff={false} />
      <Chat
        close={hide}
        setConnectionActive={setConnectionActive}
        isConnectionActive={isConnectionActive}
      />
    </div>
  );
}
