export const sourceKey = (source: string) =>
  source.startsWith("user:")
    ? "user"
    : source.startsWith("agent:")
      ? "agent"
      : source.startsWith("fact:")
        ? "fact"
        : "upload";
