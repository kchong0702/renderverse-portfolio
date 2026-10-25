import type { ChatStreamEvent, ParsedEvent } from "./types";

function parseEvent(block: string): ParsedEvent {
  let id: string | null = null;
  let retry: number | null = null;
  const data: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue;

    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    const value =
      separator === -1 ? "" : line.slice(separator + 1).replace(/^ /, "");

    if (field === "data") data.push(value);
    if (field === "id") id = value;
    if (field === "retry" && /^\d+$/.test(value)) retry = Number(value);
  }

  return {
    event: data.length
      ? (JSON.parse(data.join("\n")) as ChatStreamEvent)
      : null,
    id,
    retry,
  };
}

export async function* readEvents(
  response: Response,
): AsyncGenerator<ParsedEvent> {
  if (!response.body) throw new Error("Ezbot response has no body");
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) return;

      buffer += value;

      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const parsed = parseEvent(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (parsed.event || parsed.id || parsed.retry) yield parsed;
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}
