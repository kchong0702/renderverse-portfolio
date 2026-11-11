import { Sparkle } from "lucide-react";
import { Fragment } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import { AccountMenu, useIsAdmin, useMe } from "@/features/auth";
import { useProfile } from "@/features/portfolio";
import { cn } from "@/shared/lib/cn";
import { navGroups, useNavBadges } from "./nav";

function initials(nameOrEmail: string): string {
  const name = nameOrEmail.split("@")[0];
  const parts = name.split(/[\s._-]+/).filter(Boolean);
  return (
    parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)
  ).toUpperCase();
}

export default function Sidebar() {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const { data: profile } = useProfile();
  const name = profile?.name || me?.email;
  const badges = useNavBadges();
  const isAdmin = useIsAdmin();

  return (
    <nav
      aria-label={t("shell.mainNav")}
      className="bg-side text-side-ink flex flex-[1_1_232px] flex-col"
    >
      <div className="border-side-line flex items-center gap-2.5 border-b px-[22px] py-[22px]">
        <span className="border-side-on-border bg-side-tile text-amber-soft flex size-8 items-center justify-center rounded-lg border">
          <Sparkle size={16} />
        </span>
        <span className="flex flex-col">
          <span className="text-[17px] leading-[1.2] font-bold">
            {t("shell.product")}
          </span>
          <span className="text-side-muted text-xs/[1.6]">
            {t("shell.space")}
          </span>
        </span>
      </div>

      <div className="flex flex-col gap-0.5 overflow-y-auto overscroll-none px-3.5 py-3">
        {navGroups.map((group, index) => (
          <Fragment key={group.heading ?? index}>
            {group.heading && (
              <span className="text-side-muted px-3 pt-[18px] pb-1.5 text-xs/[1.6] font-medium">
                {t(`nav.groups.${group.heading}`)}
              </span>
            )}
            {group.items
              .filter(({ key }) => key !== "portfolio" || isAdmin)
              .map(({ key, path, icon: Icon }) => (
                <NavLink
                  key={key}
                  to={path}
                  end={path === "/"}
                  className={({ isActive }) =>
                    cn(
                      "flex min-h-10 items-center gap-3 rounded-lg px-3 no-underline",
                      isActive
                        ? "bg-side-on text-side-on-ink font-semibold"
                        : "text-side-muted font-medium",
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
                      {badges[key] && (
                        <span
                          className={cn(
                            "rounded-full px-2 py-px text-xs/[1.6] font-medium",
                            isActive
                              ? "bg-side-badge-on text-side-on-ink"
                              : "bg-side-badge text-side-muted",
                          )}
                        >
                          {badges[key]}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              ))}
          </Fragment>
        ))}
      </div>

      <div className="mb-3 min-h-4 flex-1" />

      <AccountMenu>
        <span
          aria-hidden="true"
          className="border-side-on-border text-amber-soft flex size-9 shrink-0 items-center justify-center rounded-full border text-[13px] font-semibold"
        >
          {name ? initials(name) : ""}
        </span>
        <span className="flex w-0 flex-1 flex-col">
          <span className="text-[13px] font-semibold">{name}</span>
          {profile?.headline && (
            <span
              title={profile.headline}
              className="text-side-muted truncate text-[11px]/[1.6]"
            >
              {profile.headline}
            </span>
          )}
        </span>
      </AccountMenu>
    </nav>
  );
}
