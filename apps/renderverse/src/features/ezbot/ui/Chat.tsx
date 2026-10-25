import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { FaStop } from "react-icons/fa6";
import { GrPowerReset } from "react-icons/gr";
import { IoIosSend } from "react-icons/io";
import { IoCloseSharp } from "react-icons/io5";
import { MAX_MESSAGE_CHARS } from "@/features/ezbot/api/chat/constants";
import { useChatConversation } from "@/features/ezbot/hooks/useChatConversation";
import {
  CONNECTION_STATUS,
  type ConnectionStatus,
} from "@/features/ezbot/hooks/useEzbotSession";
import { useNavigateToSection } from "@/features/ezbot/hooks/useNavigateToSection";
import styles from "./Chat.module.css";
import Chatbubble, { type ChatbubbleProps } from "./Chatbubble";
import ChatTypingIndicator from "./ChatTypingIndicator";
import { STICK_THRESHOLD_PX, SUGGESTIONS } from "./constants";

interface ChatProps {
  close: () => void;
  isOpen: boolean;
  connectionStatus: ConnectionStatus;
}

export default function Chat({ close, isOpen, connectionStatus }: ChatProps) {
  const { t } = useTranslation();
  const isOnline = connectionStatus === CONNECTION_STATUS.ONLINE;
  const {
    messages,
    isResponding,
    sendMessage,
    stopResponse,
    resetConversation,
  } = useChatConversation({ isOnline });
  const { navigate, canNavigate } = useNavigateToSection();

  const [input, setInput] = useState("");
  const chatsRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const stickToBottomRef = useRef(true);

  const isWaitingForResponse =
    isResponding && messages[messages.length - 1]?.content === "";

  const noConnectionMessage: ChatbubbleProps = {
    id: "",
    content: t("chat.offline"),
    role: "system",
    isAborted: false,
  };
  const greetingMessage: ChatbubbleProps = {
    id: "greeting",
    content: (
      <Trans i18nKey="chat.greeting" components={{ bold: <strong /> }} />
    ),
    role: "system",
  };

  const handleScroll = () => {
    const chats = chatsRef.current;
    if (!chats) return;
    stickToBottomRef.current =
      chats.scrollHeight - chats.scrollTop - chats.clientHeight <
      STICK_THRESHOLD_PX;
  };

  useLayoutEffect(() => {
    const chats = chatsRef.current;
    if (!chats || !isOpen || !stickToBottomRef.current) return;
    chats.scrollTop = chats.scrollHeight;
  }, [messages, isWaitingForResponse, isOpen]);

  useEffect(() => {
    if (!isOpen || isResponding || !isOnline) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;
    const frame = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [isOpen, isResponding, isOnline]);

  useEffect(() => {
    if (!isOpen) return;
    return stopResponse;
  }, [isOpen, stopResponse]);

  const send = (text: string) => {
    stickToBottomRef.current = true;
    sendMessage(text);
  };

  const sendInput = () => {
    if (!input.trim() || isResponding || !isOnline) return;
    setInput("");
    send(input);
  };

  const resetChat = () => {
    stickToBottomRef.current = true;
    resetConversation();
  };

  return (
    <div className={styles.chatbox}>
      <div className={styles.header}>
        <button
          type="button"
          className={styles.reset}
          aria-label={t("chat.reset")}
          onClick={(event) => {
            event.stopPropagation();
            resetChat();
          }}
        >
          <GrPowerReset size={25} aria-hidden />
        </button>
        <button
          type="button"
          className={styles.close}
          aria-label={t("chat.close")}
          onClick={(event) => {
            event.stopPropagation();
            close();
          }}
        >
          <IoCloseSharp size={30} aria-hidden />
        </button>
      </div>
      <div className={styles.chats} ref={chatsRef} onScroll={handleScroll}>
        <div className={styles.chatContainer}>
          {connectionStatus === CONNECTION_STATUS.OFFLINE ? (
            <Chatbubble {...noConnectionMessage} />
          ) : (
            <>
              {isOnline && (
                <div className={styles.greeting}>
                  <Chatbubble {...greetingMessage} />
                  <div className={styles.suggestions}>
                    {SUGGESTIONS.map((section) => (
                      <button
                        key={section}
                        type="button"
                        className={styles.suggestion}
                        disabled={isResponding}
                        onClick={(event) => {
                          event.stopPropagation();
                          send(t(`chat.suggestions.${section}`));
                        }}
                      >
                        {t(`chat.suggestions.${section}`)}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages
                .filter((message) => message.content)
                .map((message) => (
                  <Chatbubble
                    key={message.id}
                    {...message}
                    canNavigate={canNavigate}
                    onNavigate={navigate}
                  />
                ))}
            </>
          )}
          {isWaitingForResponse && <ChatTypingIndicator />}
        </div>
      </div>
      <div className={styles.chattools}>
        <input
          ref={inputRef}
          className={[styles.input, isResponding ? styles.inputMuted : ""].join(
            " ",
          )}
          type="text"
          placeholder={isResponding ? t("chat.typing") : t("chat.typeMessage")}
          value={input}
          maxLength={MAX_MESSAGE_CHARS}
          disabled={isResponding}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") sendInput();
          }}
        />
        <button
          type="button"
          className={[
            styles.send,
            isResponding || input === "" ? "" : styles.muted,
          ].join(" ")}
          aria-label={isResponding ? t("chat.stop") : t("chat.send")}
          onClick={isResponding ? stopResponse : sendInput}
        >
          {isResponding ? (
            <FaStop size={20} aria-hidden />
          ) : (
            <IoIosSend size={28} aria-hidden />
          )}
        </button>
      </div>
      <div className={styles.disclaimer}>
        <span>{t("chat.disclaimer")}</span>
      </div>
    </div>
  );
}
