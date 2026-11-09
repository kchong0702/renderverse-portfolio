import type { BadgeTone } from "@/shared/components/Badge";

export const fitTone = (fit: number): BadgeTone =>
  fit >= 70 ? "ok" : fit >= 50 ? "warn" : "neutral";
