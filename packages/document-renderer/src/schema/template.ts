// Generated from document-schema by `pnpm schema`. Do not edit.

/**
 * Such as sidebar-band
 */
export type Id = string;
/**
 * Shown in the template picker
 */
export type Name = string;
/**
 * One line for the template picker
 */
export type Description = string;
/**
 * Document kinds it lays out
 *
 * @minItems 1
 */
export type Kinds = [DocumentKind, ...DocumentKind[]];
export type DocumentKind = "resume" | "cv" | "cover_letter";
/**
 * Font of body text
 */
export type Font =
  | "inter"
  | "lato"
  | "source-sans-3"
  | "source-serif-4"
  | "merriweather"
  | "eb-garamond";
/**
 * Font of the name and section titles
 */
export type Font1 =
  | "inter"
  | "lato"
  | "source-sans-3"
  | "source-serif-4"
  | "merriweather"
  | "eb-garamond";
/**
 * Colour of titles, rules and fills
 */
export type Accent = string;
/**
 * First of the page's 12 columns it covers
 */
export type Column = number;
/**
 * Columns it covers
 */
export type Span = number;
/**
 * First row it covers; the last row grows to fill the page
 */
export type Row = number;
/**
 * Rows it covers
 */
export type Rows = number;
/**
 * Background; a fill on an area down the whole page runs onto every page
 */
export type Fill = "none" | "accent" | "tint";
export type Edge = "top" | "bottom" | "left" | "right";
/**
 * How headings and short lines sit
 */
export type Align = "left" | "center" | "justify";
/**
 * Section title style
 */
export type TitleStyle =
  "rule-after" | "rule-both" | "underline" | "strip" | "side-bar";
/**
 * How an entry places its dates
 */
export type EntryLayout = "inline" | "dates-left" | "dates-below";
/**
 * How contacts are listed
 */
export type ContactsStyle = "line" | "labelled" | "icon-tiles";
/**
 * How skills are listed
 */
export type SkillsStyle = "inline" | "outline-pills" | "filled-pills";
/**
 * A ring around the photo
 */
export type PhotoRing = boolean;
export type Region =
  "top" | "top-left" | "top-center" | "top-right" | "main" | "side";
/**
 * Where the photo sits in its region
 */
export type PhotoSpot = "none" | "top" | "start" | "end";

export interface TemplateSpec {
  id: Id;
  name: Name;
  description: Description;
  kinds: Kinds;
  body_font: Font;
  heading_font: Font1;
  accent: Accent;
  regions: Regions;
  home: Home;
  photo?: PhotoSpot;
}
/**
 * The regions it has
 */
export interface Regions {
  [k: string]: RegionSpec;
}
export interface RegionSpec {
  area?: GridArea;
  fill?: Fill;
  /**
   * A line along one edge
   */
  divider?: Edge | null;
  align?: Align;
  title?: TitleStyle;
  entry?: EntryLayout;
  contacts?: ContactsStyle;
  skills?: SkillsStyle;
  photo_ring?: PhotoRing;
}
/**
 * Where it sits on the page grid
 */
export interface GridArea {
  column?: Column;
  span?: Span;
  row?: Row;
  rows?: Rows;
}
/**
 * Region each block kind goes to unless the user places it; default for the rest
 */
export interface Home {
  [k: string]: Region;
}
