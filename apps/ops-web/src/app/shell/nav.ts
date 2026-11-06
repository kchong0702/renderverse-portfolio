import type { ComponentType } from "react";
import {
  ApplicationsIcon,
  CalendarIcon,
  DashboardIcon,
  DocumentsIcon,
  InboxIcon,
  JobsIcon,
  PortfolioIcon,
  SettingsIcon,
} from "@/shared/ui/icons";

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
  icon: ComponentType<{ size?: number }>;
}

export interface NavGroup {
  /** i18n key under nav.groups; the first group has no heading */
  heading?: "jobSearch" | "you" | "stayOnTrack";
  items: NavItem[];
}

// Sidebar order from the design
export const navGroups: NavGroup[] = [
  { items: [{ key: "dashboard", path: "/", icon: DashboardIcon }] },
  {
    heading: "jobSearch",
    items: [
      { key: "jobs", path: "/jobs", icon: JobsIcon },
      { key: "applications", path: "/applications", icon: ApplicationsIcon },
    ],
  },
  {
    heading: "you",
    items: [
      { key: "documents", path: "/documents", icon: DocumentsIcon },
      { key: "portfolio", path: "/portfolio", icon: PortfolioIcon },
    ],
  },
  {
    heading: "stayOnTrack",
    items: [
      { key: "inbox", path: "/inbox", icon: InboxIcon },
      { key: "calendar", path: "/calendar", icon: CalendarIcon },
      { key: "settings", path: "/settings", icon: SettingsIcon },
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
