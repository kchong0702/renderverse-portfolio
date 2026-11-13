import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import Panel from "@/shared/components/Panel";
import { cn } from "@/shared/lib/cn";
import { identityLinkUrl } from "../api/settings";
import { useIdentities, useUnlinkIdentity } from "../hooks/useSettings";

export default function SignInMethodsPanel() {
  const { t } = useTranslation();
  const identities = useIdentities();
  const unlink = useUnlinkIdentity();
  const linkedCount =
    identities.data?.filter(({ email }) => email !== null).length ?? 0;

  return (
    <Panel title={t("settings.signInMethods.title")}>
      {identities.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("settings.signInMethods.loadFailed", {
            reason: identities.error.message,
          })}
        </p>
      )}
      {identities.data?.map(({ provider, email, configured }) => (
        <div
          key={provider}
          className="border-hair-soft flex flex-col gap-3.5 border-t pt-3.5"
        >
          <div className="flex items-center justify-between gap-3.5">
            <span className="flex min-w-0 flex-col">
              <span className="font-semibold">
                {t(`settings.signInMethods.names.${provider}`)}
              </span>
              <span
                className={cn(
                  "text-[14px] break-words",
                  email ? "text-ok" : "text-ink-3",
                )}
              >
                {email ??
                  t(
                    !configured
                      ? "settings.signInMethods.status.not_configured"
                      : provider === "password"
                        ? "settings.signInMethods.status.password_not_linked"
                        : "settings.signInMethods.status.not_linked",
                  )}
              </span>
            </span>
            {email ? (
              <span className="flex flex-col items-end gap-1">
                <button
                  type="button"
                  className={buttonClass()}
                  disabled={linkedCount === 1 || unlink.isPending}
                  onClick={() => unlink.mutate(provider)}
                >
                  {t("settings.signInMethods.disconnect")}
                </button>
                {linkedCount === 1 && (
                  <span className="text-ink-3 text-sm">
                    {t("settings.signInMethods.lastMethod")}
                  </span>
                )}
              </span>
            ) : (
              configured &&
              provider !== "password" && (
                <a
                  href={identityLinkUrl(provider, "/settings")}
                  className={buttonClass()}
                >
                  {t("settings.signInMethods.connect")}
                </a>
              )
            )}
          </div>
        </div>
      ))}
      {unlink.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("settings.signInMethods.disconnectFailed", {
            reason: unlink.error.message,
          })}
        </p>
      )}
    </Panel>
  );
}
