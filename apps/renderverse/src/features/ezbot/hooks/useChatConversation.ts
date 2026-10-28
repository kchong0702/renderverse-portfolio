import { useCallback, useEffect, useRef, useState } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { EzbotApiError } from "@/features/ezbot/api/errors";
import { stopChat } from "@/features/ezbot/api/chat/stopChat";
import { streamChat } from "@/features/ezbot/api/chat/streamChat";
import { useChatStore } from "@/features/ezbot/state/chatStore";
import type { ChatMessage } from "@/features/ezbot/ui/types";
import { useRecheckEzbot, useRenewEzbotSession } from "./useEzbotSession";

const failureText = (error: unknown, t: TFunction): string => {
  if (!(error instanceof EzbotApiError)) return t("chat.error");
  switch (error.code) {
    case "SESSION_EXPIRED":
      return t("chat.sessionExpired");
    case "RATE_LIMITED":
      return t("chat.rateLimited", { seconds: error.retryAfterS ?? 60 });
    case "DAILY_LIMIT":
      return t("chat.dailyLimit", {
        hours: Math.max(1, Math.ceil((error.retryAfterS ?? 3600) / 3600)),
      });
    case "RESPONSE_IN_PROGRESS":
      return t("chat.responseInProgress");
    default:
      return t("chat.error");
  }
};

export const useChatConversation = ({ isOnline }: { isOnline: boolean }) => {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isResponding, setIsResponding] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const nextIdRef = useRef(0);
  const chatDispatch = useChatStore((s) => s.dispatch);
  const recheckEzbot = useRecheckEzbot();
  const renewSession = useRenewEzbotSession();

  useEffect(() => {
    chatDispatch({ type: "RESPONDING", payload: isResponding });
  }, [isResponding, chatDispatch]);

  const createMessage = (
    role: ChatMessage["role"],
    content: string,
  ): ChatMessage => ({
    id: `message-${nextIdRef.current++}`,
    role,
    content,
    isAborted: false,
    isError: false,
    intent: null,
  });

  const stopResponse = useCallback(() => {
    if (!controllerRef.current) return;
    stopChat();
    controllerRef.current.abort();
  }, []);

  const sendMessage = async (text: string) => {
    const message = text.trim();
    if (!message || isResponding || !isOnline) return;

    const userMessage = createMessage("user", message);
    const responseMessage = createMessage("system", "");
    const updateResponse = (update: (m: ChatMessage) => Partial<ChatMessage>) =>
      setMessages((current) =>
        current.map((m) =>
          m.id === responseMessage.id ? { ...m, ...update(m) } : m,
        ),
      );

    setMessages((current) => [...current, userMessage, responseMessage]);
    setIsResponding(true);
    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      for await (const event of streamChat(message, controller.signal)) {
        if (event.type === "response.output_text.delta") {
          updateResponse((m) => ({ content: m.content + event.delta }));
        } else if (event.type === "response.intent") {
          updateResponse(() => ({ intent: event.intent_type }));
        } else if (event.type === "response.failed") {
          updateResponse(() => ({ content: t("chat.error"), isError: true }));
        }
      }
    } catch (error) {
      if (controller.signal.aborted) {
        updateResponse((m) => ({
          content: m.content || t("chat.stopped"),
          isAborted: true,
        }));
        return;
      }
      console.error("Ezbot request failed:", error);
      updateResponse(() => ({ content: failureText(error, t), isError: true }));
      if (error instanceof EzbotApiError) {
        if (error.code === "SESSION_EXPIRED") renewSession();
      } else {
        recheckEzbot();
      }
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setIsResponding(false);
      }
    }
  };

  const resetConversation = () => {
    stopResponse();
    setMessages([]);
    renewSession();
  };

  return {
    messages,
    isResponding,
    sendMessage,
    stopResponse,
    resetConversation,
  };
};
