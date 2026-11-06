import type { SelectOption } from "@/shared/components/ui/fields";

// The choices the design offers. The API takes any valid value, so a value set
// elsewhere is still shown: withCurrent adds it to the list.

export const RUN_TIMES = ["08:00", "12:00", "18:00"];
export const MIN_SCORES = [60, 70, 80];
export const WORK_HOURS: [string, string][] = [
  ["09:00", "18:00"],
  ["10:00", "19:00"],
];
export const MEETING_GAPS = [15, 30, 60];

/** "08:00:00" → "08:00" */
export const hhmm = (time: string) => time.slice(0, 5);

export function withCurrent(
  options: SelectOption[],
  current: SelectOption,
): SelectOption[] {
  return options.some((option) => option.value === current.value)
    ? options
    : [...options, current];
}
