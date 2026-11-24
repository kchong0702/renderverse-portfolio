export {
  MAX_RECONNECTS,
  sendRefused,
  type Chat,
  type Conversation,
} from "./api/assistant";
export { default as AssistantDock } from "./components/AssistantDock";
export {
  useAnswerTask,
  useClearConversation,
  useConversation,
  useFollowDocument,
  useOlderMessages,
  useSendMessage,
  useStop,
} from "./hooks/useAssistant";
export { useAssistantStore, type AssistantTurn } from "./state/assistantStore";
