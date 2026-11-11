export function formatSize(bytes: number, language: string): string {
  const megabytes = bytes / (1024 * 1024);
  return new Intl.NumberFormat(language, {
    style: "unit",
    unit: megabytes < 1 ? "kilobyte" : "megabyte",
    maximumFractionDigits: 1,
  }).format(megabytes < 1 ? bytes / 1024 : megabytes);
}
