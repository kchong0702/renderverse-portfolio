import type { FitBand } from "../api/jobs";

export type FitTone = "ok" | "warn" | "neutral";

export const BAND_TONES: Record<FitBand, FitTone> = {
  excellent: "ok",
  good: "ok",
  possible: "warn",
  poor: "neutral",
};

export const FIT_INK: Record<FitTone, string> = {
  ok: "text-ok",
  warn: "text-warn",
  neutral: "text-ink-3",
};

export const fitTone = (fit: number): FitTone =>
  fit >= 70 ? "ok" : fit >= 50 ? "warn" : "neutral";
