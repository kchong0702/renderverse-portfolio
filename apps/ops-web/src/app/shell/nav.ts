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
  heading?: "jobSearch" | "you" | "stayOnTrack";
  items: NavItem[];
}

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

/** The sidebar item whose screen shows `pathname`, if any */
export function navItemAt(pathname: string): NavItem | undefined {
  return navGroups
    .flatMap((group) => group.items)
    .find(({ path }) =>
      path === "/" ? pathname === "/" : pathname.startsWith(path),
    );
}

/** Each item's count in the sidebar, such as "5 new"; features add theirs as they land */
export function useNavBadges(): Partial<Record<NavKey, string>> {
  return {};
}
