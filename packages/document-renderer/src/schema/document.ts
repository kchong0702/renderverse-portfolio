// Generated from document-schema by `pnpm schema`. Do not edit.

export type AnyDocument = ResumeDocument | LetterDocument;
/**
 * Schema version
 */
export type Format = "document/v2";
/**
 * For default headings, such as en or ms-MY
 */
export type Language = string;
/**
 * The template the document is laid out with
 */
export type Template = string;
/**
 * None uses the template's colour
 */
export type Accent = string | null;
export type Font =
  | "inter"
  | "lato"
  | "source-sans-3"
  | "source-serif-4"
  | "merriweather"
  | "eb-garamond";
/**
 * Size of body text
 */
export type Size = "small" | "medium" | "large";
/**
 * Line height as a multiple of the text size
 */
export type LineSpacing = number;
/**
 * How body text lines up
 */
export type Alignment = "left" | "justify";
/**
 * Page margins
 */
export type MarginsMm = number;
/**
 * Space between blocks
 */
export type SectionSpacingPt = number;
/**
 * Paper size
 */
export type PageSize = "a4" | "letter";
/**
 * Shape of the photo
 */
export type PhotoShape = "circle" | "rounded" | "square";
/**
 * Size of the photo
 */
export type Size1 = "small" | "medium" | "large";
/**
 * Kind of image
 */
export type MediaType = "image/png" | "image/jpeg" | "image/webp";
/**
 * Where ops keeps the file
 */
export type Uri = string;
/**
 * Résumé or CV
 */
export type Kind = "resume" | "cv";
/**
 * Stable key among the document's blocks
 */
export type Id = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden = boolean;
/**
 * Block kind
 */
export type Kind1 = "profile";
/**
 * Text as shown
 */
export type Text = string;
/**
 * Where the text came from
 */
export type Src = string[];
/**
 * Stable key among the document's blocks
 */
export type Id1 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden1 = boolean;
/**
 * Block kind
 */
export type Kind2 = "photo";
/**
 * The image in the document's assets; set only by the user
 */
export type File = string;
/**
 * Stable key among the document's blocks
 */
export type Id2 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden2 = boolean;
/**
 * Block kind
 */
export type Kind3 = "contacts";
/**
 * Stable key among the contacts
 */
export type Id3 = string;
/**
 * What the value is; picks the icon and label
 */
export type ContactKind =
  "email" | "phone" | "location" | "linkedin" | "github" | "website" | "other";
/**
 * In display order
 */
export type Items = Contact[];
/**
 * Stable key among the document's blocks
 */
export type Id4 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden3 = boolean;
/**
 * Block kind
 */
export type Kind4 = "summary";
/**
 * Text with its formatting; other markup is removed
 */
export type Html = string;
export type Align = "left" | "center" | "justify";
/**
 * Where the text came from
 */
export type Src1 = string[];
/**
 * Stable key among the document's blocks
 */
export type Id5 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden4 = boolean;
/**
 * Block kind
 */
export type Kind5 = "experience";
/**
 * Stable key among the section's items
 */
export type Id6 = string;
/**
 * Stable key among the entry's bullets
 */
export type Id7 = string;
/**
 * In display order
 */
export type Bullets = Bullet[];
/**
 * Stable key among the entry's links
 */
export type Id8 = string;
/**
 * In display order
 */
export type Links = Link[];
/**
 * YYYY or YYYY-MM
 */
export type Start = string | null;
/**
 * YYYY, YYYY-MM or present; None for a single date
 */
export type End = string | "present" | null;
/**
 * Jobs in display order
 */
export type Items1 = Job[];
/**
 * Stable key among the document's blocks
 */
export type Id9 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden5 = boolean;
/**
 * Block kind
 */
export type Kind6 = "education";
/**
 * Stable key among the section's items
 */
export type Id10 = string;
/**
 * In display order
 */
export type Bullets1 = Bullet[];
/**
 * In display order
 */
export type Links1 = Link[];
/**
 * Degrees in display order
 */
export type Items2 = Degree[];
/**
 * Stable key among the document's blocks
 */
export type Id11 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden6 = boolean;
/**
 * Block kind
 */
export type Kind7 = "projects";
/**
 * Stable key among the section's items
 */
export type Id12 = string;
/**
 * In display order
 */
export type Bullets2 = Bullet[];
/**
 * In display order
 */
export type Links2 = Link[];
/**
 * Stable key among its siblings
 */
export type Id13 = string;
/**
 * Tech stack, in display order
 */
export type Tags = Tag[];
/**
 * Projects in display order
 */
export type Items3 = Project[];
/**
 * Stable key among the document's blocks
 */
export type Id14 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden7 = boolean;
/**
 * Block kind
 */
export type Kind8 = "skills";
/**
 * Stable key among the section's skills
 */
export type Id15 = string;
/**
 * Such as Python, TypeScript
 */
export type Items5 = Tag[];
/**
 * Skill rows in display order
 */
export type Items4 = Skill[];
/**
 * Stable key among the document's blocks
 */
export type Id16 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden8 = boolean;
/**
 * Block kind
 */
export type Kind9 = "languages";
/**
 * Stable key among the section's languages
 */
export type Id17 = string;
/**
 * Languages in display order
 */
export type Items6 = LanguageSkill[];
/**
 * Stable key among the document's blocks
 */
export type Id18 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden9 = boolean;
/**
 * Block kind
 */
export type Kind10 = "certifications";
/**
 * Stable key among the section's items
 */
export type Id19 = string;
/**
 * In display order
 */
export type Bullets3 = Bullet[];
/**
 * In display order
 */
export type Links3 = Link[];
/**
 * Certifications in display order
 */
export type Items7 = Certification[];
/**
 * Stable key among the document's blocks
 */
export type Id20 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden10 = boolean;
/**
 * Block kind
 */
export type Kind11 = "awards";
/**
 * Stable key among the section's items
 */
export type Id21 = string;
/**
 * In display order
 */
export type Bullets4 = Bullet[];
/**
 * In display order
 */
export type Links4 = Link[];
/**
 * Awards in display order
 */
export type Items8 = Award[];
/**
 * Stable key among the document's blocks
 */
export type Id22 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden11 = boolean;
/**
 * Block kind
 */
export type Kind12 = "publications";
/**
 * Stable key among the section's items
 */
export type Id23 = string;
/**
 * In display order
 */
export type Bullets5 = Bullet[];
/**
 * In display order
 */
export type Links5 = Link[];
/**
 * In the order printed
 */
export type Authors = Value1[];
/**
 * Publications in display order
 */
export type Items9 = Publication[];
/**
 * Stable key among the document's blocks
 */
export type Id24 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden12 = boolean;
/**
 * Block kind
 */
export type Kind13 = "custom";
/**
 * Stable key among the section's items
 */
export type Id25 = string;
/**
 * In display order
 */
export type Bullets6 = Bullet[];
/**
 * In display order
 */
export type Links6 = Link[];
/**
 * Entries in display order
 */
export type Items10 = CustomEntry[];
/**
 * Every block, in reading order
 */
export type Blocks = (
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
/**
 * Schema version
 */
export type Format1 = "document/v2";
/**
 * For default headings, such as en or ms-MY
 */
export type Language1 = string;
/**
 * Cover letter
 */
export type Kind14 = "cover_letter";
/**
 * Stable key among the document's blocks
 */
export type Id26 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden13 = boolean;
/**
 * Block kind
 */
export type Kind15 = "recipient";
/**
 * One line each
 */
export type Address = Value1[];
/**
 * Stable key among the document's blocks
 */
export type Id27 = string;
/**
 * Kept in the document but left off the page
 */
export type Hidden14 = boolean;
/**
 * Block kind
 */
export type Kind16 = "letter";
/**
 * Stable key among the letter's paragraphs
 */
export type Id28 = string;
/**
 * The body, in order
 */
export type Paragraphs = Paragraph[];
/**
 * An image in the document's assets; set only by the user
 */
export type Signature = string | null;
/**
 * Every block, in reading order
 */
export type Blocks1 = (Profile | Photo | Contacts | Recipient | Letter)[];
/**
 * The résumé whose design this letter follows
 */
export type Matches = string | null;

export interface ResumeDocument {
  format?: Format;
  language?: Language;
  design?: Design;
  assets?: Assets;
  kind: Kind;
  content: ResumeContent;
}
/**
 * How it looks
 */
export interface Design {
  template?: Template;
  accent?: Accent;
  /**
   * A bundled font; None uses the template's
   */
  font?: Font | null;
  text_size?: Size;
  line_spacing?: LineSpacing;
  alignment?: Alignment;
  margins_mm?: MarginsMm;
  section_spacing_pt?: SectionSpacingPt;
  page_size?: PageSize;
  photo_shape?: PhotoShape;
  photo_size?: Size1;
  layouts?: Layouts;
}
/**
 * Blocks the user placed, per template; the rest go where the template puts them
 */
export interface Layouts {
  /**
   * This interface was referenced by `Layouts`'s JSON-Schema definition
   * via the `patternProperty` "^([a-z0-9-]{1,40}|custom-[0-9a-f-]{36})$".
   */
  [k: string]: {
    [k: string]: string[];
  };
}
/**
 * Files it uses, by hash
 */
export interface Assets {
  [k: string]: Asset;
}
/**
 * This interface was referenced by `Assets`'s JSON-Schema definition
 * via the `patternProperty` "^[0-9a-f]{64}$".
 *
 * This interface was referenced by `Assets1`'s JSON-Schema definition
 * via the `patternProperty` "^[0-9a-f]{64}$".
 */
export interface Asset {
  media_type: MediaType;
  uri: Uri;
}
/**
 * The words
 */
export interface ResumeContent {
  blocks: Blocks;
}
export interface Profile {
  id: Id;
  hidden?: Hidden;
  kind: Kind1;
  name: Value;
  /**
   * Line under the name, such as Senior Software Engineer
   */
  headline?: Value1 | null;
}
/**
 * Full name
 */
export interface Value {
  text: Text;
  src?: Src;
}
export interface Value1 {
  text: Text;
  src?: Src;
}
export interface Photo {
  id: Id1;
  hidden?: Hidden1;
  kind: Kind2;
  file: File;
}
export interface Contacts {
  id: Id2;
  hidden?: Hidden2;
  kind: Kind3;
  items: Items;
}
export interface Contact {
  id: Id3;
  kind: ContactKind;
  value: Value2;
  /**
   * Shown instead of the kind's label, such as Portfolio
   */
  label?: Value1 | null;
}
/**
 * As written, such as kelvin@example.com
 */
export interface Value2 {
  text: Text;
  src?: Src;
}
export interface Summary {
  id: Id4;
  hidden?: Hidden3;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind4;
  text: RichValue;
}
/**
 * The paragraph
 */
export interface RichValue {
  html: Html;
  /**
   * Paragraph alignment; None follows the document
   */
  align?: Align | null;
  src?: Src1;
}
export interface Experience {
  id: Id5;
  hidden?: Hidden4;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind5;
  items: Items1;
}
export interface Job {
  id: Id6;
  bullets?: Bullets;
  links?: Links;
  role: Value4;
  company: Value5;
  /**
   * When, such as 2022 to now
   */
  dates?: Date | null;
  /**
   * Where
   */
  location?: Value1 | null;
  /**
   * A paragraph before the bullets
   */
  description?: RichValue2 | null;
}
export interface Bullet {
  id: Id7;
  text: RichValue1;
}
/**
 * The bullet
 */
export interface RichValue1 {
  html: Html;
  /**
   * Paragraph alignment; None follows the document
   */
  align?: Align | null;
  src?: Src1;
}
export interface Link {
  id: Id8;
  url: Value3;
  /**
   * Shown instead of the address, such as GitHub
   */
  label?: Value1 | null;
}
/**
 * http or https address
 */
export interface Value3 {
  text: Text;
  src?: Src;
}
/**
 * Job title
 */
export interface Value4 {
  text: Text;
  src?: Src;
}
/**
 * Employer
 */
export interface Value5 {
  text: Text;
  src?: Src;
}
export interface Date {
  text: Value6;
  start?: Start;
  end?: End;
}
/**
 * As written, such as 2022 to now
 */
export interface Value6 {
  text: Text;
  src?: Src;
}
export interface RichValue2 {
  html: Html;
  /**
   * Paragraph alignment; None follows the document
   */
  align?: Align | null;
  src?: Src1;
}
export interface Education {
  id: Id9;
  hidden?: Hidden5;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind6;
  items: Items2;
}
export interface Degree {
  id: Id10;
  bullets?: Bullets1;
  links?: Links1;
  degree: Value7;
  school: Value8;
  /**
   * When
   */
  dates?: Date | null;
  /**
   * Where the school is
   */
  location?: Value1 | null;
  /**
   * Such as First Class or GPA 3.8
   */
  grade?: Value1 | null;
}
/**
 * Such as BSc Computer Science
 */
export interface Value7 {
  text: Text;
  src?: Src;
}
/**
 * Where it was earned
 */
export interface Value8 {
  text: Text;
  src?: Src;
}
export interface Projects {
  id: Id11;
  hidden?: Hidden6;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind7;
  items: Items3;
}
export interface Project {
  id: Id12;
  bullets?: Bullets2;
  links?: Links2;
  name: Value9;
  /**
   * What the user did on it
   */
  role?: Value1 | null;
  /**
   * When
   */
  dates?: Date | null;
  /**
   * What it is
   */
  description?: RichValue2 | null;
  tags?: Tags;
}
/**
 * Project name
 */
export interface Value9 {
  text: Text;
  src?: Src;
}
export interface Tag {
  id: Id13;
  text: Value10;
}
/**
 * The tag, such as a skill
 */
export interface Value10 {
  text: Text;
  src?: Src;
}
export interface Skills {
  id: Id14;
  hidden?: Hidden7;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind8;
  items: Items4;
}
export interface Skill {
  id: Id15;
  /**
   * Such as Languages; None shows just the items
   */
  label?: Value1 | null;
  items: Items5;
}
export interface Languages {
  id: Id16;
  hidden?: Hidden8;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind9;
  items: Items6;
}
export interface LanguageSkill {
  id: Id17;
  language: Value11;
  /**
   * Such as Native or C1
   */
  fluency?: Value1 | null;
}
/**
 * Such as Malay
 */
export interface Value11 {
  text: Text;
  src?: Src;
}
export interface Certifications {
  id: Id18;
  hidden?: Hidden9;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind10;
  items: Items7;
}
export interface Certification {
  id: Id19;
  bullets?: Bullets3;
  links?: Links3;
  name: Value12;
  /**
   * Who awarded it
   */
  issuer?: Value1 | null;
  /**
   * When it was earned
   */
  date?: Date | null;
}
/**
 * Such as AWS Solutions Architect
 */
export interface Value12 {
  text: Text;
  src?: Src;
}
export interface Awards {
  id: Id20;
  hidden?: Hidden10;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind11;
  items: Items8;
}
export interface Award {
  id: Id21;
  bullets?: Bullets4;
  links?: Links4;
  title: Value13;
  /**
   * Who gave it
   */
  awarder?: Value1 | null;
  /**
   * When
   */
  date?: Date | null;
}
/**
 * Such as Dean's List
 */
export interface Value13 {
  text: Text;
  src?: Src;
}
export interface Publications {
  id: Id22;
  hidden?: Hidden11;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind12;
  items: Items9;
}
export interface Publication {
  id: Id23;
  bullets?: Bullets5;
  links?: Links5;
  title: Value14;
  authors?: Authors;
  /**
   * Journal or conference
   */
  venue?: Value1 | null;
  /**
   * When it was published
   */
  date?: Date | null;
  /**
   * Such as 10.1145/1234567
   */
  doi?: Value1 | null;
}
/**
 * Title as published
 */
export interface Value14 {
  text: Text;
  src?: Src;
}
export interface Custom {
  id: Id24;
  hidden?: Hidden12;
  /**
   * As written; None uses the template's title
   */
  heading?: Value1 | null;
  kind: Kind13;
  /**
   * A paragraph before the items
   */
  text?: RichValue2 | null;
  items?: Items10;
}
export interface CustomEntry {
  id: Id25;
  bullets?: Bullets6;
  links?: Links6;
  title: Value15;
  /**
   * Second line
   */
  subtitle?: Value1 | null;
  /**
   * When
   */
  dates?: Date | null;
  /**
   * Where
   */
  location?: Value1 | null;
}
/**
 * Main line
 */
export interface Value15 {
  text: Text;
  src?: Src;
}
export interface LetterDocument {
  format?: Format1;
  language?: Language1;
  design?: Design1;
  assets?: Assets1;
  kind: Kind14;
  content: LetterContent;
  matches?: Matches;
}
/**
 * How it looks
 */
export interface Design1 {
  template?: Template;
  accent?: Accent;
  /**
   * A bundled font; None uses the template's
   */
  font?: Font | null;
  text_size?: Size;
  line_spacing?: LineSpacing;
  alignment?: Alignment;
  margins_mm?: MarginsMm;
  section_spacing_pt?: SectionSpacingPt;
  page_size?: PageSize;
  photo_shape?: PhotoShape;
  photo_size?: Size1;
  layouts?: Layouts;
}
/**
 * Files it uses, by hash
 */
export interface Assets1 {
  [k: string]: Asset;
}
/**
 * The words
 */
export interface LetterContent {
  blocks: Blocks1;
}
export interface Recipient {
  id: Id26;
  hidden?: Hidden13;
  kind: Kind15;
  /**
   * Such as Aisha Rahman
   */
  name?: Value1 | null;
  /**
   * Such as Talent Lead
   */
  title?: Value1 | null;
  /**
   * Such as Lumen Pay
   */
  organization?: Value1 | null;
  address?: Address;
}
export interface Letter {
  id: Id27;
  hidden?: Hidden14;
  kind: Kind16;
  /**
   * As written
   */
  date?: Value1 | null;
  /**
   * Such as Application for Senior Backend Engineer
   */
  subject?: Value1 | null;
  greeting: Value16;
  paragraphs: Paragraphs;
  closing: Value17;
  signature?: Signature;
}
/**
 * Such as Dear Ms Rahman,
 */
export interface Value16 {
  text: Text;
  src?: Src;
}
export interface Paragraph {
  id: Id28;
  text: RichValue3;
}
/**
 * The paragraph
 */
export interface RichValue3 {
  html: Html;
  /**
   * Paragraph alignment; None follows the document
   */
  align?: Align | null;
  src?: Src1;
}
/**
 * Such as Yours sincerely,
 */
export interface Value17 {
  text: Text;
  src?: Src;
}
