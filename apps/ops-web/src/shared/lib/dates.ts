const DAY_MS = 86_400_000;

export function localDateTime(at: Date): string {
  return new Date(at.getTime() - at.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

export function relativeDay(value: string, language: string): string {
  const day = new Date(value.length === 10 ? `${value}T00:00` : value);
  const today = new Date();
  const days = Math.round(
    (new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime() -
      new Date(
        today.getFullYear(),
        today.getMonth(),
        today.getDate(),
      ).getTime()) /
      DAY_MS,
  );
  return new Intl.RelativeTimeFormat(language, { numeric: "auto" }).format(
    days,
    "day",
  );
}
