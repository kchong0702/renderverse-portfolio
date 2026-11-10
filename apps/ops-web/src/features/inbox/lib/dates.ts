const DAY_MS = 86_400_000;

export function daysAgo(time: Date): number {
  const day = new Date(time);
  day.setHours(0, 0, 0, 0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((today.getTime() - day.getTime()) / DAY_MS);
}
