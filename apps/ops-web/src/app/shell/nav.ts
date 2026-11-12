import { createLucideIcon, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useApplications } from "@/features/applications";
import { useIsAdmin } from "@/features/auth";
import { reviewCards, useChanges } from "@/features/data";
import { useInbox } from "@/features/inbox";
import { useJobs } from "@/features/jobs";
import { useDraft } from "@/features/portfolio";
import { useGoogleAccount } from "@/features/settings";

export type NavKey =
  | "dashboard"
  | "jobs"
  | "applications"
  | "documents"
  | "portfolio"
  | "data"
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
  {
    items: [
      {
        key: "dashboard",
        path: "/",
        icon: createLucideIcon("Dashboard", [
          [
            "rect",
            { x: "3", y: "3", width: "7", height: "9", rx: "1", key: "0" },
          ],
          [
            "rect",
            { x: "14", y: "3", width: "7", height: "5", rx: "1", key: "1" },
          ],
          [
            "rect",
            { x: "14", y: "12", width: "7", height: "9", rx: "1", key: "2" },
          ],
          [
            "rect",
            { x: "3", y: "16", width: "7", height: "5", rx: "1", key: "3" },
          ],
        ]),
      },
    ],
  },
  {
    heading: "jobSearch",
    items: [
      {
        key: "jobs",
        path: "/jobs",
        icon: createLucideIcon("Jobs", [
          ["circle", { cx: "12", cy: "12", r: "9", key: "0" }],
          ["path", { d: "m15.5 8.5-2 5-5 2 2-5z", key: "1" }],
        ]),
      },
      {
        key: "applications",
        path: "/applications",
        icon: createLucideIcon("Applications", [
          [
            "rect",
            { x: "3", y: "7", width: "18", height: "13", rx: "2", key: "0" },
          ],
          ["path", { d: "M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2", key: "1" }],
        ]),
      },
    ],
  },
  {
    heading: "you",
    items: [
      {
        key: "documents",
        path: "/documents",
        icon: createLucideIcon("Documents", [
          [
            "path",
            {
              d: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z",
              key: "0",
            },
          ],
          ["path", { d: "M14 3v5h5M9 13h6M9 17h6", key: "1" }],
        ]),
      },
      {
        key: "portfolio",
        path: "/portfolio",
        icon: createLucideIcon("Portfolio", [
          [
            "path",
            {
              d: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
              key: "0",
            },
          ],
        ]),
      },
      {
        key: "data",
        path: "/data",
        icon: createLucideIcon("Data", [
          [
            "path",
            {
              d: "M5 5h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM9 9a2 2 0 1 0 0 4a2 2 0 1 0 0-4zM6 16c.6-1.4 1.7-2 3-2s2.4.6 3 2M15 10h3M15 14h3",
              key: "0",
            },
          ],
        ]),
      },
    ],
  },
  {
    heading: "stayOnTrack",
    items: [
      {
        key: "inbox",
        path: "/inbox",
        icon: createLucideIcon("Inbox", [
          ["path", { d: "M22 12h-6l-2 3h-4l-2-3H2", key: "0" }],
          [
            "path",
            {
              d: "M5.5 5h13l3.5 7v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z",
              key: "1",
            },
          ],
        ]),
      },
      {
        key: "calendar",
        path: "/calendar",
        icon: createLucideIcon("Calendar", [
          [
            "rect",
            { x: "3", y: "5", width: "18", height: "16", rx: "2", key: "0" },
          ],
          ["path", { d: "M16 3v4M8 3v4M3 10h18", key: "1" }],
        ]),
      },
      {
        key: "settings",
        path: "/settings",
        icon: createLucideIcon("Settings", [
          ["circle", { cx: "12", cy: "12", r: "3", key: "0" }],
          [
            "path",
            {
              d: "M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1",
              key: "1",
            },
          ],
        ]),
      },
    ],
  },
];

export function navItemAt(pathname: string): NavItem | undefined {
  return navGroups
    .flatMap((group) => group.items)
    .find(({ path }) =>
      path === "/" ? pathname === "/" : pathname.startsWith(path),
    );
}

export function useNavBadges(): Partial<Record<NavKey, string>> {
  const { t } = useTranslation();
  const newJobs = useJobs().data?.new_count;
  const active = useApplications().data?.filter((a) => a.stage !== "closed");
  const { account } = useGoogleAccount();
  const inbox = useInbox(account !== null);
  const { data: draft } = useDraft(useIsAdmin());
  const { data: changes } = useChanges();
  const waiting = changes ? reviewCards(changes).length : 0;
  return {
    jobs: newJobs ? t("nav.badges.newJobs", { count: newJobs }) : undefined,
    applications: active?.length ? String(active.length) : undefined,
    inbox: inbox.data?.needs_reply ? String(inbox.data.needs_reply) : undefined,
    portfolio:
      draft?.site_url && draft.changes.length > 0
        ? t("nav.badges.draft", { count: draft.changes.length })
        : undefined,
    data: waiting ? String(waiting) : undefined,
  };
}
