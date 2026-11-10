import type { TFunction } from "i18next";

export const sourceKey = (source: string) =>
  source.startsWith("user:")
    ? "user"
    : source.startsWith("agent:")
      ? "agent"
      : source.startsWith("fact:")
        ? "fact"
        : "upload";

export const sourceName = (
  t: TFunction,
  source: string,
  lines: { id: string; text: string }[],
) => {
  const line = lines.find(({ id }) => id === source);
  return line
    ? t("documents.sources.line", { text: line.text })
    : t(`documents.sources.${sourceKey(source)}`);
};
