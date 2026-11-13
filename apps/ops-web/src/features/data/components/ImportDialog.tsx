import { Check, LoaderCircle, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { isActive } from "@/features/imports";
import { buttonClass } from "@/shared/components/button";
import { dayMonth } from "@/shared/lib/dates";
import { formatSize } from "@/shared/lib/size";
import { cn } from "@/shared/lib/cn";
import { useImportFile, useImports } from "../hooks/useData";

const ACCEPT = [".pdf", ".docx", ".zip"];

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function ImportDialog({ open, onClose }: ImportDialogProps) {
  const { t, i18n } = useTranslation();
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const upload = useImportFile();
  const imports = useImports();
  const [file, setFile] = useState<File | null>(null);
  const [sent, setSent] = useState(false);
  const [wrongType, setWrongType] = useState<string | null>(null);
  const result =
    upload.data &&
    (imports.data?.find((row) => row.id === upload.data.id) ?? upload.data);
  const again = upload.data?.status === "done";

  useEffect(() => {
    if (open) dialog.current?.showModal();
    else dialog.current?.close();
  }, [open]);

  const choose = (chosen: File | undefined) => {
    if (!chosen) return;
    const fits = ACCEPT.some((ending) =>
      chosen.name.toLowerCase().endsWith(ending),
    );
    setWrongType(fits ? null : chosen.name);
    setFile(fits ? chosen : null);
    upload.reset();
  };
  const finish = () => {
    upload.reset();
    setFile(null);
    onClose();
  };
  const step =
    upload.isPending || (result && isActive(result))
      ? "reading"
      : result?.status === "done"
        ? "done"
        : "pick";

  return (
    <dialog
      ref={dialog}
      aria-labelledby="import-heading"
      onClose={() => (step === "done" ? finish() : onClose())}
      className="bg-panel text-ink shadow-float m-auto mt-[72px] w-[calc(100%-32px)] max-w-[520px] rounded-2xl p-0 backdrop:bg-[rgb(28_25_23/0.4)]"
    >
      <div className="flex flex-col gap-5 p-6 sm:p-7">
        {step === "pick" && (
          <>
            <div className="flex flex-col gap-1.5">
              <h2 id="import-heading" className="m-0 text-lg font-semibold">
                {t("data.importDialog.title")}
              </h2>
              <p className="text-ink-2 m-0 text-sm">
                {t("data.importDialog.intro")}
              </p>
            </div>
            <input
              ref={input}
              type="file"
              accept={ACCEPT.join(",")}
              className="sr-only"
              tabIndex={-1}
              onChange={(event) => {
                choose(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
            {file ? (
              <div className="bg-well flex items-center gap-3 rounded-xl px-3.5 py-3">
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="font-semibold [overflow-wrap:anywhere]">
                    {file.name}
                  </span>
                  <span className="text-ink-3 text-[13px]">
                    {formatSize(file.size, i18n.language)}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="text-amber min-h-9 cursor-pointer text-sm font-semibold"
                >
                  {t("data.importDialog.remove")}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => input.current?.click()}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  choose(event.dataTransfer.files[0]);
                }}
                className="border-hair text-ink-2 hover:border-ink-3 flex cursor-pointer flex-col items-center gap-2 rounded-xl border-[1.5px] border-dashed px-4 py-8"
              >
                <Upload size={26} strokeWidth={1.6} className="text-ink-3" />
                <span className="text-sm">
                  <span className="text-ink font-semibold">
                    {t("data.importDialog.choose")}
                  </span>{" "}
                  {t("data.importDialog.orDrop")}
                </span>
                <span className="text-ink-3 text-[13px]">
                  {t("data.importDialog.types")}
                </span>
              </button>
            )}
            {(wrongType || upload.isError || result?.status === "failed") && (
              <p role="alert" className="text-crit m-0 text-sm">
                {wrongType
                  ? t("data.importDialog.wrongType", { name: wrongType })
                  : t("data.importDialog.failed", {
                      reason: upload.error?.message ?? result?.error,
                    })}
              </p>
            )}
            <div className="flex flex-wrap justify-end gap-2.5">
              <button type="button" onClick={onClose} className={buttonClass()}>
                {t("data.cancel")}
              </button>
              <button
                type="button"
                disabled={!file}
                onClick={() => {
                  if (!file) return;
                  setSent(false);
                  upload.mutate({ file, onSent: () => setSent(true) });
                }}
                className={buttonClass("primary")}
              >
                {t("data.importDialog.add")}
              </button>
            </div>
          </>
        )}
        {step === "reading" && (
          <>
            <div className="flex flex-col gap-1.5">
              <h2 id="import-heading" className="m-0 text-lg font-semibold">
                {t("data.importDialog.reading", { name: file?.name })}
              </h2>
              <p className="text-ink-2 m-0 text-sm">
                {t("data.importDialog.keepsGoing")}
              </p>
            </div>
            <ol role="status" className="m-0 flex list-none flex-col gap-3 p-0">
              {[
                {
                  label: t("data.importDialog.sending"),
                  done: sent && !upload.isPending,
                },
                { label: t("data.importDialog.comparing"), done: false },
              ].map((item, index) => (
                <li
                  key={item.label}
                  className={cn(
                    "flex items-center gap-3 text-sm",
                    item.done ? "text-ink-2" : "text-ink",
                  )}
                >
                  {item.done ? (
                    <span className="bg-ok flex size-[18px] items-center justify-center rounded-full text-white">
                      <Check size={12} strokeWidth={3} />
                    </span>
                  ) : index === 0 || (sent && !upload.isPending) ? (
                    <LoaderCircle
                      size={18}
                      className="text-amber animate-spin"
                    />
                  ) : (
                    <span className="border-hair size-[18px] rounded-full border-2" />
                  )}
                  {item.label}
                </li>
              ))}
            </ol>
            {result?.status === "queued" && result.error && (
              <p role="alert" className="text-crit m-0 text-sm">
                {t("data.importDialog.retrying", { reason: result.error })}
              </p>
            )}
            <div className="flex justify-end">
              <button type="button" onClick={onClose} className={buttonClass()}>
                {t("data.importDialog.close")}
              </button>
            </div>
          </>
        )}
        {step === "done" && result && (
          <>
            <div className="flex flex-col gap-1.5">
              <h2 id="import-heading" className="m-0 text-lg font-semibold">
                {again
                  ? t("data.importDialog.again", {
                      date: dayMonth(
                        new Date(result.created_at),
                        i18n.language,
                      ),
                    })
                  : t("data.importDialog.done")}
              </h2>
              <p className="text-ink-2 m-0 text-sm [overflow-wrap:anywhere]">
                {again ? t("data.importDialog.sameFile") : result.filename}
              </p>
            </div>
            {!again && (
              <dl className="m-0 flex flex-col">
                {[
                  {
                    key: "added" as const,
                    count: result.added,
                    tone: "text-ok",
                  },
                  {
                    key: "conflicts" as const,
                    count: result.conflicts,
                    tone: "text-warn",
                  },
                  {
                    key: "matched" as const,
                    count: result.matched,
                    tone: "text-ink-3",
                  },
                ].map((group) => (
                  <div
                    key={group.key}
                    className="border-hair-soft flex justify-between gap-4 border-b py-3"
                  >
                    <dt className="flex flex-col gap-0.5">
                      <span className="font-semibold">
                        {t(`data.importDialog.groups.${group.key}.label`)}
                      </span>
                      <span className="text-ink-3 text-[13px]">
                        {t(`data.importDialog.groups.${group.key}.hint`)}
                      </span>
                    </dt>
                    <dd
                      className={cn(
                        "m-0 text-lg font-semibold",
                        group.count ? group.tone : "text-ink-3",
                      )}
                    >
                      {group.count}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            <div className="flex flex-wrap justify-end gap-2.5">
              <button
                type="button"
                onClick={finish}
                className={
                  result.conflicts ? buttonClass() : buttonClass("primary")
                }
              >
                {t("data.importDialog.finish")}
              </button>
              {result.conflicts > 0 && (
                <Link
                  to="/data/review"
                  onClick={finish}
                  className={buttonClass("primary")}
                >
                  {t("data.importDialog.chooseNow")}
                </Link>
              )}
            </div>
          </>
        )}
      </div>
    </dialog>
  );
}
