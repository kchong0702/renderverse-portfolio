import { useEffect, useState } from "react";

export function useCopied() {
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(null), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  return {
    copied,
    copy: (key: string, text: string) =>
      navigator.clipboard.writeText(text).then(() => setCopied(key)),
  };
}
