import type { BadgeTone } from "@/shared/components/Badge";
import type { FitBand } from "../api/jobs";

export const BAND_TONES: Record<FitBand, BadgeTone> = {
  excellent: "ok",
  good: "ok",
  possible: "warn",
  poor: "neutral",
};

export const fitTone = (fit: number): BadgeTone =>
  fit >= 70 ? "ok" : fit >= 50 ? "warn" : "neutral";
