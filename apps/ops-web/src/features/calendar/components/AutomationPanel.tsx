import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useUpdateSettings } from "@/features/settings";

export default function AutomationPanel({
  followUpReminders,
}: {
  followUpReminders: boolean;
}) {
  const { t } = useTranslation();
  const headingId = useId();
  const update = useUpdateSettings();

  return (
    <section
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex flex-col gap-3 rounded-xl border px-5 py-[18px]"
    >
      <h2 id={headingId} className="text-ink m-0 text-[15px] font-semibold">
        {t("calendar.automation")}
      </h2>
      <label className="flex items-start gap-3 text-[14px]">
        <input
          type="checkbox"
          checked={followUpReminders}
          onChange={(event) =>
            update.mutate({
              automation: { follow_up_reminders: event.target.checked },
            })
          }
          className="mt-0.5 size-[18px] shrink-0 accent-[#b45309]"
        />
        {t("settings.automation.rules.follow_up_reminders.label")}
      </label>
      {update.isError && (
        <span role="alert" className="text-crit text-[13px]">
          {t("settings.save.failed", { reason: update.error.message })}
        </span>
      )}
      <Link
        to="/settings"
        className="text-amber text-[14px] font-semibold no-underline"
      >
        {t("calendar.changeInSettings")}
      </Link>
    </section>
  );
}
