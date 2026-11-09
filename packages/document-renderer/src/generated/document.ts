/**
 * Generated code. Do not edit manually.
 *
 * Regenerate using: pnpm schema
 * Source: json_schemas()
 */

export type AnyDocument = ResumeDocument | LetterDocument;
export type Font =
  | "inter"
  | "lato"
  | "source-sans-3"
  | "source-serif-4"
  | "merriweather"
  | "eb-garamond";
export type Size = "small" | "medium" | "large";
export type PageSize = "a4" | "letter";
export type PhotoShape = "circle" | "rounded" | "square";
export type Region =
  "top" | "top-left" | "top-center" | "top-right" | "main" | "side";
export type MediaType = "image/png" | "image/jpeg" | "image/webp";
export type ContactKind =
  "email" | "phone" | "location" | "linkedin" | "github" | "website" | "other";
export type Align = "left" | "center" | "justify";

export interface ResumeDocument {
  format?: "document/v1";
  language?: string;
  design?: Design;
  assets?: {
    [k: string]: Asset;
  };
  kind: "resume" | "cv";
  content: ResumeContent;
}
export interface Design {
  template?: string;
  accent?: string | null;
  font?: Font | null;
  text_size?: Size;
  line_spacing?: number;
  alignment?: "left" | "justify";
  margins_mm?: number;
  section_spacing_pt?: number;
  page_size?: PageSize;
  photo_shape?: PhotoShape;
  photo_size?: Size;
  layouts?: Placement[];
}
export interface Placement {
  template: string;
  region: Region;
  blocks: string[];
}
export interface Asset {
  media_type: MediaType;
  uri: string;
}
export interface ResumeContent {
  blocks: (
    | Profile
    | Photo
    | Contacts
    | Summary
    | Experience
    | Education
    | Projects
    | Skills
    | Languages
    | Certifications
    | Awards
    | Publications
    | Custom
  )[];
}
export interface Profile {
  id: string;
  hidden?: boolean;
  kind: "profile";
  name: Value;
  headline?: Value | null;
}
export interface Value {
  text: string;
  src?: string[];
}
export interface Photo {
  id: string;
  hidden?: boolean;
  kind: "photo";
  file: string;
}
export interface Contacts {
  id: string;
  hidden?: boolean;
  kind: "contacts";
  items: Contact[];
}
export interface Contact {
  id: string;
  kind: ContactKind;
  value: Value;
  label?: Value | null;
}
export interface Summary {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "summary";
  text: RichValue;
}
export interface RichValue {
  html: string;
  align?: Align | null;
  src?: string[];
}
export interface Experience {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "experience";
  items: Job[];
}
export interface Job {
  id: string;
  bullets?: Bullet[];
  links?: Link[];
  role: Value;
  company: Value;
  dates?: Date | null;
  location?: Value | null;
  description?: RichValue | null;
}
export interface Bullet {
  id: string;
  text: RichValue;
}
export interface Link {
  id: string;
  url: Value;
  label?: Value | null;
}
export interface Date {
  text: Value;
  start?: string | null;
  end?: string | "present" | null;
}
export interface Education {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "education";
  items: Degree[];
}
export interface Degree {
  id: string;
  bullets?: Bullet[];
  links?: Link[];
  degree: Value;
  school: Value;
  dates?: Date | null;
  location?: Value | null;
  grade?: Value | null;
}
export interface Projects {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "projects";
  items: Project[];
}
export interface Project {
  id: string;
  bullets?: Bullet[];
  links?: Link[];
  name: Value;
  role?: Value | null;
  dates?: Date | null;
  description?: RichValue | null;
  tags?: Tag[];
}
export interface Tag {
  id: string;
  text: Value;
}
export interface Skills {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "skills";
  items: Skill[];
}
export interface Skill {
  id: string;
  label?: Value | null;
  items: Tag[];
}
export interface Languages {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "languages";
  items: LanguageSkill[];
}
export interface LanguageSkill {
  id: string;
  language: Value;
  fluency?: Value | null;
}
export interface Certifications {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "certifications";
  items: Certification[];
}
export interface Certification {
  id: string;
  bullets?: Bullet[];
  links?: Link[];
  name: Value;
  issuer?: Value | null;
  date?: Date | null;
}
export interface Awards {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "awards";
  items: Award[];
}
export interface Award {
  id: string;
  bullets?: Bullet[];
  links?: Link[];
  title: Value;
  awarder?: Value | null;
  date?: Date | null;
}
export interface Publications {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "publications";
  items: Publication[];
}
export interface Publication {
  id: string;
  bullets?: Bullet[];
  links?: Link[];
  title: Value;
  authors?: Value[];
  venue?: Value | null;
  date?: Date | null;
  doi?: Value | null;
}
export interface Custom {
  id: string;
  hidden?: boolean;
  heading?: Value | null;
  kind: "custom";
  text?: RichValue | null;
  items?: CustomEntry[];
}
export interface CustomEntry {
  id: string;
  bullets?: Bullet[];
  links?: Link[];
  title: Value;
  subtitle?: Value | null;
  dates?: Date | null;
  location?: Value | null;
}
export interface LetterDocument {
  format?: "document/v1";
  language?: string;
  design?: Design;
  assets?: {
    [k: string]: Asset;
  };
  kind: "cover_letter";
  content: LetterContent;
  matches?: string | null;
}
export interface LetterContent {
  blocks: (Profile | Photo | Contacts | Recipient | Letter)[];
}
export interface Recipient {
  id: string;
  hidden?: boolean;
  kind: "recipient";
  name?: Value | null;
  title?: Value | null;
  organization?: Value | null;
  address?: Value[];
}
export interface Letter {
  id: string;
  hidden?: boolean;
  kind: "letter";
  date?: Value | null;
  subject?: Value | null;
  greeting: Value;
  paragraphs: Paragraph[];
  closing: Value;
  signature?: string | null;
}
export interface Paragraph {
  id: string;
  text: RichValue;
}
