import { Sparkle } from "lucide-react";
import { useId, useRef } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/ui/button";
import { useAssistantStore } from "../../state/assistantStore";

/** The floating assistant button and the panel it opens, about `topic` */
export default function AssistantDock({ topic }: { topic?: string }) {
  const { t, i18n } = useTranslation();
  const open = useAssistantStore((state) => state.open);
  const setOpen = useAssistantStore((state) => state.setOpen);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const statusId = useId();

  const close = () => {
    setOpen(false);
    toggleRef.current?.focus();
  };

  return (
    <div
      onKeyDown={(event) => open && event.key === "Escape" && close()}
      className="fixed right-7 bottom-7 z-30 flex flex-col items-end gap-3"
    >
      {open && (
        <section
          id={panelId}
          aria-label={t("assistant.title")}
          className="bg-panel border-hair shadow-float flex w-[360px] max-w-[calc(100vw-56px)] flex-col rounded-2xl border"
        >
          <div className="border-hair-soft flex flex-col gap-0.5 border-b px-[18px] py-4">
            <span className="flex items-center gap-2 font-semibold">
              <span className="text-amber flex">
                <Sparkle size={16} />
              </span>
              {t("assistant.title")}
            </span>
            <span className="text-ink-3 text-[13px]">
              {topic
                ? t("assistant.askAbout", {
                    topic: topic.toLocaleLowerCase(i18n.language),
                  })
                : t("assistant.askAnything")}
            </span>
          </div>
          <p
            id={statusId}
            className="text-ink-3 m-0 px-[18px] py-4 text-[13px]"
          >
            {t("assistant.notConnected")}
          </p>
          <div className="flex items-end gap-2 px-[18px] pb-[18px]">
            <label className="flex flex-1">
              <span className="sr-only">{t("assistant.message")}</span>
              <textarea
                rows={2}
                disabled
                aria-describedby={statusId}
                placeholder={t("assistant.placeholder")}
                className="border-hair bg-ground text-ink min-h-10 flex-1 resize-none rounded-lg border px-3 py-2 text-sm leading-normal disabled:opacity-60"
              />
            </label>
            <button type="button" disabled className={buttonClass("primary")}>
              {t("assistant.send")}
            </button>
          </div>
        </section>
      )}
      <button
        ref={toggleRef}
        type="button"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen(!open)}
        className="bg-primary text-on-primary flex min-h-[52px] cursor-pointer items-center gap-2.5 rounded-full pr-5 pl-4 font-semibold shadow-[0_8px_24px_rgb(28_25_23/0.22)]"
      >
        <span className="text-amber-soft flex">
          <Sparkle size={20} />
        </span>
        {t(open ? "assistant.close" : "assistant.open")}
      </button>
    </div>
  );
}
