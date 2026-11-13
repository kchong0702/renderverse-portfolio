import { useEffect, useId, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import type { Application } from "@/features/applications";
import { GoogleNotice } from "@/features/settings";
import { ApiError, RunFailed } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import type { Email } from "../api/inbox";
import { useDraftFollowUp } from "../hooks/useInbox";
import { daysAgo } from "../lib/dates";
import type { Thread } from "../lib/threads";

interface FollowUpsProps {
  applications: Application[];
  threads: Thread[];
  onDrafted: (email: Email) => void;
}

export default function FollowUps({
  applications,
  threads,
  onDrafted,
}: FollowUpsProps) {
  const { t } = useTranslation();
  const headingId = useId();
  const draft = useDraftFollowUp();
  const [params, setParams] = useSearchParams();
  const asked = useRef(params.get("followUp"));
  const start = (application: Application) =>
    draft.mutate(application.id, {
      onSuccess: (result) =>
        onDrafted({
          to:
            threads.find(
              ({ application_id }) => application_id === application.id,
            )?.from_email ?? "",
          subject: t("inbox.followUp.subject", { role: application.role }),
          body: result.body,
        }),
    });

  useEffect(() => {
    const application = applications.find(({ id }) => id === asked.current);
    asked.current = null;
    if (!application) return;
    setParams({}, { replace: true });
    start(application);
  });
  const due = applications
    .flatMap((application) =>
      application.stage === "applied" && application.applied_on
        ? [
            {
              application,
              days: daysAgo(new Date(`${application.applied_on}T00:00`)),
            },
          ]
        : [],
    )
    .filter(({ days }) => days >= 7)
    .sort((a, b) => b.days - a.days);

  if (due.length === 0) return null;

  return (
    <section
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex flex-col gap-2 rounded-xl border px-[18px] py-4"
    >
      <h2 id={headingId} className="text-ink m-0 text-[15px] font-semibold">
        {t("inbox.followUps")}
      </h2>
      {due.map(({ application, days }) => (
        <div key={application.id} className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-3">
            <span className="flex flex-col">
              <span className="font-semibold">{application.company}</span>
              <span className="text-warn text-[13px]">
                {t("inbox.noReply", { days })}
              </span>
            </span>
            <button
              type="button"
              className={buttonClass()}
              disabled={draft.isPending}
              onClick={() => start(application)}
            >
              {t("inbox.followUp.draft")}
            </button>
          </div>
          {draft.variables === application.id &&
            (draft.isPending ? (
              <span className="text-ink-3 text-[13px]">
                {t("inbox.followUp.drafting")}
              </span>
            ) : draft.error instanceof RunFailed ? (
              <span className="flex flex-col items-start gap-2">
                <span role="alert" className="text-[13px]">
                  {draft.error.message}
                </span>
                {draft.error.next && (
                  <Link
                    to={`/${draft.error.next.screen}`}
                    className={buttonClass()}
                  >
                    {draft.error.next.label}
                  </Link>
                )}
              </span>
            ) : draft.isError ? (
              draft.error instanceof ApiError && draft.error.status === 409 ? (
                <GoogleNotice
                  problem="reconnect"
                  reason={draft.error.message}
                  next="/inbox"
                />
              ) : (
                <span role="alert" className="text-crit text-[13px]">
                  {t("inbox.followUp.failed", { reason: draft.error.message })}
                </span>
              )
            ) : null)}
        </div>
      ))}
    </section>
  );
}
