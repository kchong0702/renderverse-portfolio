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
