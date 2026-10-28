import type { PortfolioSection } from "@/features/portfolio";

export type ChatStreamEvent =
  | { type: "response.output_text.delta"; delta: string }
  | { type: "response.intent"; intent_type: PortfolioSection }
  | { type: "response.completed" }
  | { type: "response.cancelled" }
  | { type: "response.failed"; error: { code: string; message: string } };

export type ChatStreamEventType = ChatStreamEvent["type"];

export interface ParsedEvent {
  event: ChatStreamEvent | null;
  id: string | null;
  retry: number | null;
}
