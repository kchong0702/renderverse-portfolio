import type { Vec3 } from "@/experience/state/sceneStore";

export interface ProjectItem {
  proj_id: string;
  proj_name: string;
  short_desc: string;
  proj_desc: string;
  proj_link: string;
  github_link: string | null;
  img_path: string | null;
  proj_stack: string[];
  vid_path: string | null;
}

export interface SkillItem {
  name: string;
  rating: number;
}

/** sites/<user_id>/release/current.json, which Ops publishes */
export interface Release {
  number: number;
  published_at: string;
  about: {
    name: string;
    headline: string;
    summary: string;
    location: string;
    links: (string | { label: string; url: string })[];
  };
  skills: { id: string; name: string; group: string }[];
  projects: {
    id: string;
    title: string;
    organisation: string;
    start: string | null;
    end: string | null;
    summary: string;
    highlights: string[];
    link?: string | null;
    code_link?: string | null;
    tools?: string[];
    image: string | null;
    video: string | null;
  }[];
}

export type PortfolioSection = "skills" | "projects" | "about" | "contact";

export interface SectionFit {
  facing: Vec3;
  width: number;
  height: number;
  rise: number;
  minDistance?: number;
  maxDistance: number;
}
