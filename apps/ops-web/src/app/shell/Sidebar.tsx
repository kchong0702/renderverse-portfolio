import { Fragment } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import { SignOutButton, useMe } from "@/features/auth";
import { cn } from "@/shared/lib/cn";
import { SparkIcon } from "@/shared/ui/icons";
import { navGroups } from "./nav";
import ThemeToggle from "./ThemeToggle";

function initials(email: string): string {
  const name = email.split("@")[0];
  const parts = name.split(/[._-]+/).filter(Boolean);
  return (
    parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)
  ).toUpperCase();
}

export default function Sidebar() {
  const { t } = useTranslation();
  const { data: me } = useMe();

  return (
    <nav
      aria-label={t("shell.mainNav")}
      className="bg-side text-side-ink flex flex-[1_1_232px] flex-col"
    >
      <div className="border-side-line flex items-center gap-2.5 border-b px-[22px] py-[22px]">
        <span className="border-side-on-border bg-side-tile text-amber-soft flex size-8 items-center justify-center rounded-lg border">
          <SparkIcon size={16} />
        </span>
        <span className="flex flex-col">
          <span className="text-[17px] leading-tight font-bold">
            {t("shell.product")}
          </span>
          <span className="text-side-muted text-xs">{t("shell.tagline")}</span>
        </span>
      </div>

      <div className="flex flex-col gap-0.5 px-3.5 py-3">
        {navGroups.map((group, index) => (
          <Fragment key={group.heading ?? index}>
            {group.heading && (
              <span className="text-side-muted px-3 pt-[18px] pb-1.5 text-xs font-medium">
                {t(`nav.groups.${group.heading}`)}
              </span>
            )}
            {group.items.map(({ key, path, icon: Icon }) => (
              <NavLink
                key={key}
                to={path}
                end={path === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-10 items-center gap-3 rounded-lg px-3 no-underline",
                    isActive
                      ? "bg-side-on text-side-on-ink font-semibold"
                      : "text-side-muted hover:text-side-ink font-medium",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={cn(
                        "flex",
                        isActive ? "text-amber-soft" : "text-side-muted",
                      )}
                    >
                      <Icon />
                    </span>
                    <span className="flex-1">{t(`nav.items.${key}`)}</span>
                  </>
                )}
              </NavLink>
            ))}
          </Fragment>
        ))}
      </div>

      <div className="min-h-4 flex-1" />

      <div className="border-side-line bg-side-foot flex items-center gap-3 border-t px-[22px] py-4">
        <span
          aria-hidden="true"
          className="border-side-on-border text-amber-soft flex size-9 shrink-0 items-center justify-center rounded-full border text-[13px] font-semibold"
        >
          {me ? initials(me.email) : ""}
        </span>
        <span className="min-w-0 truncate text-[13px] font-semibold">
          {me?.email}
        </span>
        <span className="ml-auto flex">
          <ThemeToggle />
          <SignOutButton />
        </span>
      </div>
    </nav>
  );
}
