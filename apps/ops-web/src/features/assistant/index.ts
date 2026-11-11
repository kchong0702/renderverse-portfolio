export { default as AssistantDock } from "./components/AssistantDock";
export {
  useAnswerTask,
  useFollowTurn,
  useResumeTurns,
  useSendMessage,
  useStop,
} from "./hooks/useAssistant";
export {
  openTurn,
  useAssistantStore,
  type AssistantTurn,
  type ChatEntry,
} from "./state/assistantStore";
