import type { DocumentBody, DocumentKind } from "../api/documents";

export interface StarterText {
  name: string;
  greeting: string;
  closing: string;
}

export function starterBody(
  kind: DocumentKind,
  text: StarterText,
  source: string,
): DocumentBody {
  const value = (words: string) => ({ text: words, src: [source] });
  const paragraph = { html: "", src: [source] };
  const profile = { kind: "profile", id: "profile", name: value(text.name) };
  return {
    kind,
    content: {
      blocks:
        kind === "cover_letter"
          ? [
              profile,
              {
                kind: "letter",
                id: "letter",
                greeting: value(text.greeting),
                paragraphs: [{ id: "p1", text: paragraph }],
                closing: value(text.closing),
              },
            ]
          : [profile, { kind: "summary", id: "summary", text: paragraph }],
    },
  };
}
