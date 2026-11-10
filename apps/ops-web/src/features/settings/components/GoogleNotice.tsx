import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import { googleConnectUrl } from "../api/settings";

interface GoogleNoticeProps {
  problem: "not_configured" | "not_connected" | "expired";
  next: string;
}

export default function GoogleNotice({ problem, next }: GoogleNoticeProps) {
  const { t } = useTranslation();

  return (
    <div
      role="status"
      className="bg-panel border-hair flex flex-wrap items-center justify-between gap-4 rounded-xl border px-[26px] py-6"
    >
      <p className="text-ink-2 m-0 max-w-[60ch] text-sm">
        {t(`googleNotice.${problem}`)}
      </p>
      {problem !== "not_configured" && (
        <a href={googleConnectUrl(next)} className={buttonClass("primary")}>
          {t(
            problem === "expired"
              ? "googleNotice.reconnect"
              : "googleNotice.connect",
          )}
        </a>
      )}
    </div>
  );
}
