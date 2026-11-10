export function addDays(day: Date, days: number): Date {
  const next = new Date(day);
  next.setDate(next.getDate() + days);
  return next;
}

export function startOfDay(day: Date): Date {
  const start = new Date(day);
  start.setHours(0, 0, 0, 0);
  return start;
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
