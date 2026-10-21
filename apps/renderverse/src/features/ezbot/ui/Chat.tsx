import { useTranslation } from "react-i18next";
import styles from "./Chat.module.css";
import { IoCloseSharp } from "react-icons/io5";
import { GrPowerReset } from "react-icons/gr";
import { IoIosSend } from "react-icons/io";
import Chatbubble, { type ChatbubbleProps } from "./Chatbubble";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  MAX_HISTORY,
  MAX_MESSAGE_CHARS,
  streamChat,
  type ChatHistoryMessage,
} from "@/features/ezbot/api/ezbot";
import ChatLoader from "./ChatLoader";
import { FaStop } from "react-icons/fa6";
import {
  CONNECTION_STATUS,
  useRecheckEzbot,
  type ConnectionStatus,
} from "@/features/ezbot/hooks/useEzbotStatus";

interface ChatMessage {
  id: string;
  role: "user" | "system";
  content: string;
  isAborted: boolean;
  isError: boolean;
}

interface ChatProps {
  close: () => void;
  isOpen: boolean;
  connectionStatus: ConnectionStatus;
  setReplying: (isReplying: boolean) => void;
}

// Completed turns sent back to ezbot as context, oldest first
const toHistory = (messages: ChatMessage[]): ChatHistoryMessage[] =>
  messages
    .filter((message) => message.content && !message.isError)
    .slice(-MAX_HISTORY)
    .map((message): ChatHistoryMessage => ({
      role: message.role === "user" ? "user" : "assistant",
      content: message.content,
    }));

export default function Chat(props: ChatProps) {
  const { t } = useTranslation();
  const noConnectionMessage: ChatbubbleProps = {
    id: "",
    content: t("chat.offline"),
    role: "system",
    isAborted: false,
  };

  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const chatFocusRef = useRef<HTMLDivElement>(null);
  const replyControllerRef = useRef<AbortController | null>(null);
  const nextIdRef = useRef(0);

  const { isOpen, connectionStatus, setReplying } = props;
  const recheckEzbot = useRecheckEzbot();

  const scrollToBottom = () => {
    chatFocusRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
      inline: "nearest",
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const abortReply = useCallback(() => {
    replyControllerRef.current?.abort();
  }, []);

  // Cancel any reply when the chat closes
  useEffect(() => {
    if (!isOpen) return;
    return abortReply;
  }, [isOpen, abortReply]);

  useEffect(() => {
    setReplying(isTyping);
  }, [isTyping, setReplying]);

  const createMessage = (
    role: ChatMessage["role"],
    content: string,
  ): ChatMessage => ({
    id: `message-${nextIdRef.current++}`,
    role,
    content,
    isAborted: false,
    isError: false,
  });

  const sendMessage = async () => {
    const message = input.trim();
    if (!message || isTyping || connectionStatus !== CONNECTION_STATUS.ONLINE)
      return;

    const history = toHistory(chatHistory);
    const userMessage = createMessage("user", message);
    const replyMessage = createMessage("system", "");

    const updateReply = (update: (m: ChatMessage) => Partial<ChatMessage>) =>
      setChatHistory((messages) =>
        messages.map((m) =>
          m.id === replyMessage.id ? { ...m, ...update(m) } : m,
        ),
      );

    setChatHistory((messages) => [...messages, userMessage, replyMessage]);
    setInput("");
    setIsTyping(true);

    const controller = new AbortController();
    replyControllerRef.current = controller;

    try {
      for await (const { event, data } of streamChat(
        { message, history },
        controller.signal,
      )) {
        if (event === "token") {
          updateReply((m) => ({ content: m.content + data.content }));
        } else if (event === "error") {
          updateReply(() => ({ content: t("chat.error"), isError: true }));
        }
      }
    } catch (error) {
      if (controller.signal.aborted) {
        updateReply((m) => ({
          content: m.content || t("chat.stopped"),
          isAborted: true,
        }));
      } else {
        console.error("Ezbot request failed:", error);
        updateReply(() => ({ content: t("chat.error"), isError: true }));
        recheckEzbot();
      }
    } finally {
      // A newer reply may have started after a reset, leave its state alone
      if (replyControllerRef.current === controller) {
        replyControllerRef.current = null;
        setIsTyping(false);
      }
    }
  };

  const resetChat = () => {
    abortReply();
    setChatHistory([]);
  };

  const isWaitingForReply =
    isTyping && chatHistory[chatHistory.length - 1]?.content === "";

  return (
    <div className={styles.chatbox}>
      <div className={styles.header}>
        <div className={styles.reset}>
          <GrPowerReset
            size={25}
            style={{
              color: "white",
            }}
            onClick={(event) => {
              event.stopPropagation();
              resetChat();
            }}
          />
        </div>
        <div className={styles.close}>
          <IoCloseSharp
            size={30}
            style={{
              color: "white",
            }}
            onClick={(event) => {
              event.stopPropagation();
              props.close();
            }}
          />
        </div>
      </div>
      <div className={styles.chats}>
        <div className={styles.chatContainer}>
          {connectionStatus === CONNECTION_STATUS.OFFLINE ? (
            <Chatbubble {...noConnectionMessage} />
          ) : (
            chatHistory
              .filter((message) => message.content)
              .map((message) => <Chatbubble key={message.id} {...message} />)
          )}
          {isWaitingForReply && <ChatLoader />}
          <div ref={chatFocusRef} />
        </div>
      </div>
      <div className={styles.chattools}>
        <input
          className={[styles.input, isTyping ? styles.inputMuted : ""].join(
            " ",
          )}
          type="text"
          placeholder={isTyping ? t("chat.typing") : t("chat.typeMessage")}
          value={input}
          maxLength={MAX_MESSAGE_CHARS}
          disabled={isTyping}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              sendMessage();
            }
          }}
        />
        <div
          className={[
            styles.send,
            isTyping || input === "" ? "" : styles.muted,
          ].join(" ")}
        >
          {isTyping ? (
            <FaStop size={20} onClick={abortReply} />
          ) : (
            <IoIosSend size={28} onClick={sendMessage} />
          )}
        </div>
      </div>
      <div className={styles.disclaimer}>
        <span>{t("chat.disclaimer")}</span>
      </div>
    </div>
  );
}
