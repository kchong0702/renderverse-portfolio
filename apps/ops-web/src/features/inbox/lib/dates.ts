const DAY_MS = 86_400_000;

export function daysAgo(time: Date): number {
  const day = new Date(time.getFullYear(), time.getMonth(), time.getDate());
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((today.getTime() - day.getTime()) / DAY_MS);
}
