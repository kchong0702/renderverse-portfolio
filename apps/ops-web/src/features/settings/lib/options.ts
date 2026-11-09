import type { SelectOption } from "@/shared/components/fields";

export const RUN_TIMES = ["08:00", "12:00", "18:00"];
export const MIN_SCORES = [60, 70, 80];
export const WORK_HOURS: [string, string][] = [
  ["09:00", "18:00"],
  ["10:00", "19:00"],
];
export const MEETING_GAPS = [15, 30, 60];

export const hhmm = (time: string) => time.slice(0, 5);

export function withCurrent(
  options: SelectOption[],
  current: SelectOption,
): SelectOption[] {
  return options.some((option) => option.value === current.value)
    ? options
    : [...options, current];
}
