import styles from "./Chat.module.css";
import PropTypes from "prop-types";
import { IoCloseSharp } from "react-icons/io5";
import { GrPowerReset } from "react-icons/gr";
import { IoIosSend } from "react-icons/io";
import Chatbubble from "./Chatbubble";
import { useCallback, useEffect, useRef, useState } from "react";
import { connect } from "../../core/api/ws";
import ChatLoader from "./ChatLoader";
import { FaStop } from "react-icons/fa6";

export default function Chat(props) {
  const noConnectionMessage = {
    id: "",
    content: "Ezbot is asleep, contact support to wake him up 🤖💤",
    semantic: "None",
    feedback: "",
    role: "system",
    question_id: "",
    isAborted: false,
  };

  const [chatHistory, setChatHistory] = useState([]);
  const [input, setInput] = useState("");
  const [ws, setWs] = useState(null);
  const [isTyping, setIsTyping] = useState(false);

  const chatFocusRef = useRef(null);

  const { setConnectionActive } = props;

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

  const sendMessage = () => {
    if (ws && input && !isTyping) {
      const latestQuery = memoizedChatMessageHandler(input, "user");
      const history = chatHistory.slice(1).map((chat) => {
        return {
          role: chat.role,
          content: chat.content,
        };
      });
      const newQuery = {
        query: {
          role: latestQuery.role,
          content: latestQuery.content,
        },
        history: history,
        question_id: latestQuery.id,
        action: "query",
      };
      console.log(JSON.stringify(newQuery));
      ws.send(JSON.stringify(newQuery));
      setInput("");
    }
  };

  const abortMessage = () => {
    if (isTyping) {
      console.log("aborted");
      const questionId = chatHistory[chatHistory.length - 1].id;
      ws.send(
        JSON.stringify({
          question_id: questionId,
          action: "abort",
        }),
      );
    }
  };

  const memoizedChatMessageHandler = useCallback(
    (content, role, question_id = null, isAborted = false) => {
      const timestamp = Date.now();
      const nextId = `${sessionStorage.getItem("sessionId")}-${timestamp}`;
      const chatMessage = {
        id: nextId,
        content: content,
        semantic: "None",
        feedback: "",
        role: role,
        question_id: question_id,
        isAborted: isAborted,
      };

      setChatHistory((history) => [...history, chatMessage]);

      return chatMessage;
    },
    [],
  );

  useEffect(() => {
    const receivedMessage = (aiResponse) => {
      if (aiResponse.finish_reason === "typing") {
        setIsTyping(true);
      } else if (aiResponse.finish_reason === "aborted") {
        memoizedChatMessageHandler(
          aiResponse.response,
          aiResponse.role,
          aiResponse.question_id,
          true,
        );
        setIsTyping(false);
      } else {
        memoizedChatMessageHandler(
          aiResponse.response,
          aiResponse.role,
          aiResponse.question_id,
          false,
        );
        setIsTyping(false);
      }
    };

    const initChat = async () => {
      const socket = await connect();

      socket.addEventListener("open", () => {
        console.log("Ezbot connection established");
        setConnectionActive(true);
      });

      socket.addEventListener("message", (event) => {
        const response = JSON.parse(event.data);
        receivedMessage(response);
      });

      socket.addEventListener("close", (event) => {
        if (event.code === 1008) {
          console.error(event.reason);
        }
      });

      socket.addEventListener("error", (error) => {
        console.error("WebSocket error:", error);
        setConnectionActive(false);
      });

      setWs(socket);

      // cleanup
      return () => {
        socket.close();
      };
    };

    initChat();
  }, [memoizedChatMessageHandler, setConnectionActive]);

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
              setChatHistory([]);
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
          {!props.isConnectionActive ? (
            <Chatbubble {...noConnectionMessage} />
          ) : (
            chatHistory.map((message) => (
              <Chatbubble key={message.id} {...message} />
            ))
          )}
          {isTyping && <ChatLoader />}
          <div ref={chatFocusRef} />
        </div>
      </div>
      <div className={styles.chattools}>
        <input
          className={[styles.input, isTyping ? styles.inputMuted : ""].join(
            " ",
          )}
          type="text"
          placeholder={isTyping ? "Ezbot is typing..." : "Type a message"}
          value={input}
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
            <FaStop size={20} onClick={abortMessage} />
          ) : (
            <IoIosSend size={28} onClick={sendMessage} />
          )}
        </div>
      </div>
      <div className={styles.disclaimer}>
        <span>Ezbot can make mistakes. Consider checking important info</span>
      </div>
    </div>
  );
}

Chat.propTypes = {
  close: PropTypes.func,
  setConnectionActive: PropTypes.func,
  isConnectionActive: PropTypes.bool,
};
