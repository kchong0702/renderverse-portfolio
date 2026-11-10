import type {
  AnyDocument,
  Bullet,
  Link,
  RichValue,
} from "./generated/document";
import type { PhotoSpot } from "./generated/template";
import type { AnyBlock, Spec } from "./layout/place";

export type Translate = (key: string) => string;

export interface Context {
  document: AnyDocument;
  spec: Spec;
  photo: PhotoSpot;
  assetUrl: (hash: string) => string;
  t: Translate;
}

export type Block<K extends AnyBlock["kind"]> = Extract<AnyBlock, { kind: K }>;

export interface BlockProps<K extends AnyBlock["kind"]> {
  block: Block<K>;
  ctx: Context;
}

export type SectionKind = Exclude<
  AnyBlock["kind"],
  "profile" | "photo" | "contacts" | "recipient" | "letter"
>;

export type EntryKind =
  | "experience"
  | "education"
  | "projects"
  | "certifications"
  | "awards"
  | "publications"
  | "custom";

export interface EntryView {
  id: string;
  title: string;
  subtitle?: string;
  dates?: string;
  place?: string;
  note?: string;
  text?: RichValue | null;
  bullets?: Bullet[];
  links?: Link[];
  tags?: string[];
}

export interface EntryFields {
  title: string;
  subtitle: string;
  dates: string;
  place?: string;
}

export interface EntryProps {
  entry: EntryView;
  path: string;
  fields: EntryFields;
}
