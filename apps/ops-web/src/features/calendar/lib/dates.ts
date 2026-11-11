export function addDays(day: Date, days: number): Date {
  const next = new Date(day);
  next.setDate(next.getDate() + days);
  return next;
}

export function startOfDay(day: Date): Date {
  return new Date(day.getFullYear(), day.getMonth(), day.getDate());
}

export function mondayOf(day: Date): Date {
  return addDays(startOfDay(day), -((day.getDay() + 6) % 7));
}

export function isoDay(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, "0");
  return `${day.getFullYear()}-${month}-${String(day.getDate()).padStart(2, "0")}`;
}

export const eventTime = (value: string, allDay: boolean) =>
  new Date(allDay ? `${value}T00:00` : value);

export function monthDays(day: Date): Date[] {
  const first = new Date(day.getFullYear(), day.getMonth(), 1);
  const length =
    ((first.getDay() + 6) % 7) +
    new Date(day.getFullYear(), day.getMonth() + 1, 0).getDate();
  return Array.from({ length: Math.ceil(length / 7) * 7 }, (_, index) =>
    addDays(mondayOf(first), index),
  );
}

export const shiftAnchor = (
  anchor: Date,
  view: "week" | "month",
  by: number,
) =>
  view === "month"
    ? new Date(anchor.getFullYear(), anchor.getMonth() + by, 1)
    : addDays(anchor, 7 * by);
