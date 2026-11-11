import type { AnyDocument } from "@renderverse/document-renderer";
import type { DocumentKind } from "../api/documents";

export interface StarterText {
  name: string;
  greeting: string;
  closing: string;
}

export function starterBody(
  kind: DocumentKind,
  text: StarterText,
  source: string,
): AnyDocument {
  const value = (words: string) => ({ text: words, src: [source] });
  const paragraph = { html: "", src: [source] };
  const profile = {
    kind: "profile" as const,
    id: "profile",
    name: value(text.name),
  };
  return kind === "cover_letter"
    ? {
        kind,
        content: {
          blocks: [
            profile,
            {
              kind: "letter",
              id: "letter",
              greeting: value(text.greeting),
              paragraphs: [{ id: "p1", text: paragraph }],
              closing: value(text.closing),
            },
          ],
        },
      }
    : {
        kind,
        content: {
          blocks: [
            profile,
            { kind: "summary", id: "summary", text: paragraph },
          ],
        },
      };
}
