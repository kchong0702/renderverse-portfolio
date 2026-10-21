import { useTranslation } from "react-i18next";
import styles from "./Chat.module.css";
import PropTypes from "prop-types";
import { IoCloseSharp } from "react-icons/io5";
import { GrPowerReset } from "react-icons/gr";
import { IoIosSend } from "react-icons/io";
import Chatbubble from "./Chatbubble";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  MAX_HISTORY,
  MAX_MESSAGE_CHARS,
  streamChat,
} from "../../core/api/ezbot";
import ChatLoader from "./ChatLoader";
import { FaStop } from "react-icons/fa6";
import { CONNECTION_STATUS, useRecheckEzbot } from "../../hooks/useEzbotStatus";

// Completed turns sent back to ezbot as context, oldest first
const toHistory = (messages) =>
  messages
    .filter((message) => message.content && !message.isError)
    .slice(-MAX_HISTORY)
    .map((message) => ({
      role: message.role === "user" ? "user" : "assistant",
      content: message.content,
    }));

export default function Chat(props) {
  const { t } = useTranslation();
  const noConnectionMessage = {
    id: "",
    content: t("chat.offline"),
    role: "system",
    isAborted: false,
  };

  const [chatHistory, setChatHistory] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const chatFocusRef = useRef(null);
  const replyControllerRef = useRef(null);
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

  const createMessage = (role, content) => ({
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

    const updateReply = (update) =>
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

Chat.propTypes = {
  close: PropTypes.func,
  isOpen: PropTypes.bool,
  connectionStatus: PropTypes.oneOf(Object.values(CONNECTION_STATUS)),
  setReplying: PropTypes.func,
};
