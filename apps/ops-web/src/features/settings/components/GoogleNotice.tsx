import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import { googleConnectUrl } from "../api/settings";

type GoogleNoticeProps =
  | { problem: "not_configured" | "not_connected"; next: string }
  | { problem: "reconnect"; reason: string; next: string };

export default function GoogleNotice(props: GoogleNoticeProps) {
  const { t } = useTranslation();

  return (
    <div
      role="status"
      className="bg-panel border-hair flex flex-wrap items-center justify-between gap-4 rounded-xl border px-[26px] py-6"
    >
      <p className="text-ink-2 m-0 max-w-[60ch] text-sm">
        {props.problem === "reconnect"
          ? props.reason
          : t(`googleNotice.${props.problem}`)}
      </p>
      {props.problem !== "not_configured" && (
        <a
          href={googleConnectUrl(props.next)}
          className={buttonClass("primary")}
        >
          {t(
            props.problem === "reconnect"
              ? "googleNotice.reconnect"
              : "googleNotice.connect",
          )}
        </a>
      )}
    </div>
  );
}
