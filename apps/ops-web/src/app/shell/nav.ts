import {
  Briefcase,
  Calendar,
  Compass,
  FileText,
  Folder,
  Inbox,
  LayoutDashboard,
  Settings,
  type LucideIcon,
} from "lucide-react";

export type NavKey =
  | "dashboard"
  | "jobs"
  | "applications"
  | "documents"
  | "portfolio"
  | "inbox"
  | "calendar"
  | "settings";

export interface NavItem {
  key: NavKey;
  path: string;
  icon: LucideIcon;
}

export interface NavGroup {
  /** i18n key under nav.groups; the first group has no heading */
  heading?: "jobSearch" | "you" | "stayOnTrack";
  items: NavItem[];
}

// Sidebar order from the design. Badges arrive with each feature's count hook.
export const navGroups: NavGroup[] = [
  { items: [{ key: "dashboard", path: "/", icon: LayoutDashboard }] },
  {
    heading: "jobSearch",
    items: [
      { key: "jobs", path: "/jobs", icon: Compass },
      { key: "applications", path: "/applications", icon: Briefcase },
    ],
  },
  {
    heading: "you",
    items: [
      { key: "documents", path: "/documents", icon: FileText },
      { key: "portfolio", path: "/portfolio", icon: Folder },
    ],
  },
  {
    heading: "stayOnTrack",
    items: [
      { key: "inbox", path: "/inbox", icon: Inbox },
      { key: "calendar", path: "/calendar", icon: Calendar },
      { key: "settings", path: "/settings", icon: Settings },
    ],
  },
];
