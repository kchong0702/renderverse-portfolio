import type { PortfolioSection } from "@/features/portfolio";

/** One bubble in the conversation */
export interface ChatMessage {
  id: string;
  role: "user" | "system";
  content: string;
  isAborted: boolean;
  isError: boolean;
  intent: PortfolioSection | null;
}
