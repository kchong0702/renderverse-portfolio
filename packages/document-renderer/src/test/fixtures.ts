import type { AnyDocument } from "../generated/document";

const value = (text: string) => ({ text, src: ["p1.s1"] });
const rich = (html: string) => ({ html, src: ["p1.s2"] });

export const PHOTO = "a".repeat(64);

export const resume = (
  overrides: Partial<Extract<AnyDocument, { kind: "resume" | "cv" }>> = {},
): AnyDocument => ({
  kind: "resume",
  content: {
    blocks: [
      {
        kind: "profile",
        id: "profile",
        name: value("Kelvin Chong"),
        headline: value("Senior Engineer"),
      },
      { kind: "photo", id: "photo", file: PHOTO },
      {
        kind: "contacts",
        id: "contacts",
        items: [
          { id: "c1", kind: "email", value: value("kelvin@example.com") },
          { id: "c2", kind: "github", value: value("github.com/kelvin") },
        ],
      },
      {
        kind: "summary",
        id: "sum",
        text: rich("Backend engineer with <b>7 years</b> of payments."),
      },
      {
        kind: "experience",
        id: "exp",
        items: [
          {
            id: "acme",
            role: value("Senior Engineer"),
            company: value("Acme Corp"),
            dates: {
              text: value("2022 to now"),
              start: "2022",
              end: "present",
            },
            bullets: [
              { id: "b1", text: rich("Led the migration of 30 services.") },
            ],
          },
        ],
      },
      {
        kind: "skills",
        id: "sk",
        items: [
          {
            id: "s1",
            label: value("Languages"),
            items: [{ id: "t1", text: value("Python") }],
          },
        ],
      },
    ],
  },
  assets: {
    [PHOTO]: { media_type: "image/png", uri: "s3://assets/photo.png" },
  },
  ...overrides,
});
