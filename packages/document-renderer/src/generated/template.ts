/**
 * Generated code. Do not edit manually.
 *
 * Regenerate using: pnpm schema
 * Source: json_schemas()
 */

export type DocumentKind = "resume" | "cv" | "cover_letter";
export type Font =
  | "inter"
  | "lato"
  | "source-sans-3"
  | "source-serif-4"
  | "merriweather"
  | "eb-garamond";
export type Fill = "none" | "accent" | "tint";
export type Edge = "top" | "bottom" | "left" | "right";
export type Align = "left" | "center" | "justify";
export type TitleStyle =
  "rule-after" | "rule-both" | "underline" | "strip" | "side-bar";
export type EntryLayout = "inline" | "dates-left" | "dates-below";
export type ContactsStyle = "line" | "labelled" | "icon-tiles";
export type SkillsStyle = "inline" | "outline-pills" | "filled-pills";
export type Region =
  "top" | "top-left" | "top-center" | "top-right" | "main" | "side";
export type PhotoSpot = "none" | "top" | "start" | "end";

export interface TemplateSpec {
  id: string;
  name: string;
  description: string;
  kinds: [DocumentKind, ...DocumentKind[]];
  body_font: Font;
  heading_font: Font;
  accent: string;
  regions: {
    [k: string]: RegionSpec;
  };
  layout: {
    [k: string]: Region;
  };
  photo?: PhotoSpot;
}
export interface RegionSpec {
  area?: GridArea;
  fill?: Fill;
  divider?: Edge | null;
  align?: Align;
  title?: TitleStyle;
  entry?: EntryLayout;
  contacts?: ContactsStyle;
  skills?: SkillsStyle;
  photo_ring?: boolean;
}
export interface GridArea {
  column?: number;
  span?: number;
  row?: number;
  rows?: number;
}
