import { Menu, Sparkle, X } from "lucide-react";
import { Fragment, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import { AccountMenu, useIsAdmin, useMe } from "@/features/auth";
import { ProcessingIndicator } from "@/features/imports";
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
  const name = profile && (profile.name || me?.email);
  const badges = useNavBadges();
  const isAdmin = useIsAdmin();
  const [open, setOpen] = useState(false);

  return (
    <nav
      aria-label={t("shell.mainNav")}
      onKeyDown={(event) => event.key === "Escape" && setOpen(false)}
      className="bg-side text-side-ink sticky top-0 z-40 flex flex-[1_1_232px] flex-col"
    >
      <div className="border-side-line flex h-14 items-center gap-2.5 border-b pr-2 pl-4 shell:h-auto shell:p-[22px]">
        <span className="border-side-on-border bg-side-tile text-amber-soft flex size-7 items-center justify-center rounded-lg border shell:size-8">
          <Sparkle size={16} />
        </span>
        <span className="flex flex-col">
          <span className="text-base leading-[1.2] font-bold shell:text-[17px]">
            {t("shell.product")}
          </span>
          <span className="text-side-muted hidden text-xs/[1.6] shell:block">
            {t("shell.space")}
          </span>
        </span>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="main-nav-links"
          aria-label={t(open ? "shell.closeMenu" : "shell.openMenu")}
          onClick={() => setOpen(!open)}
          className="text-side-ink ml-auto flex size-11 cursor-pointer items-center justify-center rounded-lg border-0 bg-transparent shell:hidden"
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <div
        id="main-nav-links"
        className={cn(
          "bg-side min-h-0 flex-1 flex-col shell:static shell:flex",
          open ? "fixed inset-x-0 top-14 bottom-0 flex" : "hidden",
        )}
      >
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
                    onClick={() => setOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        "flex min-h-11 items-center gap-3 rounded-lg px-3 no-underline shell:min-h-10",
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

        <div className="mb-3 flex min-h-4 flex-1 flex-col justify-end px-3.5">
          <ProcessingIndicator onClick={() => setOpen(false)} />
        </div>

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
      </div>
    </nav>
  );
}
