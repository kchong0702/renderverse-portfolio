import type { Vec3 } from "@/experience/state/sceneStore";

export interface ProjectItem {
  proj_id: number;
  proj_name: string;
  short_desc: string;
  proj_desc: string;
  proj_link: string;
  github_link: string | null;
  img_path: string;
  proj_stack: string[];
  vid_path: string;
}

export interface SkillItem {
  name: string;
  rating: number;
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
