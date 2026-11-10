const DAY_MS = 86_400_000;

export function localDateTime(at: Date): string {
  return new Date(at.getTime() - at.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

export function daysFromToday(value: string): number {
  const day = new Date(value.length === 10 ? `${value}T00:00` : value);
  const today = new Date();
  return Math.round(
    (new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime() -
      new Date(
        today.getFullYear(),
        today.getMonth(),
        today.getDate(),
      ).getTime()) /
      DAY_MS,
  );
}

export function relativeDay(value: string, language: string): string {
  return new Intl.RelativeTimeFormat(language, { numeric: "auto" }).format(
    daysFromToday(value),
    "day",
  );
}

export function dayMonth(at: Date, language: string): string {
  return `${at.getDate()} ${new Intl.DateTimeFormat(language, { month: "short" }).format(at)}`;
}
