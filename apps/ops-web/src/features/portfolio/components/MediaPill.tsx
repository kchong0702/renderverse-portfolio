import { X } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/shared/api/http";
import { cn } from "@/shared/lib/cn";
import { MEDIA_TYPES, type MediaSlot } from "../api/media";
import type { Entry } from "../api/profile";
import { useRemoveMedia, useUploadMedia } from "../hooks/useMedia";

const pill =
  "border-hair inline-flex min-h-7 items-center gap-1.5 rounded-full border px-3 text-[13px] font-medium";

export default function MediaPill({
  project,
  slot,
}: {
  project: Entry;
  slot: MediaSlot;
}) {
  const { t } = useTranslation();
  const input = useRef<HTMLInputElement>(null);
  const upload = useUploadMedia();
  const remove = useRemoveMedia();
  const [progress, setProgress] = useState(0);
  const label = t(`portfolio.media.${slot}`);
  const name = project.title;
  const failed = upload.isError
    ? upload.error instanceof ApiError
      ? t("portfolio.media.uploadFailed", {
          label,
          reason: upload.error.message,
        })
      : upload.error.message
    : remove.isError
      ? t("portfolio.media.removeFailed", {
          label,
          reason: remove.error.message,
        })
      : null;

  return (
    <>
      <input
        ref={input}
        type="file"
        accept={MEDIA_TYPES[slot].join(",")}
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          setProgress(0);
          upload.mutate({
            projectId: project.id,
            slot,
            file,
            onProgress: setProgress,
          });
        }}
      />
      {upload.isPending ? (
        <span role="status" className={cn(pill, "text-ink-3")}>
          {t(`portfolio.media.uploading.${slot}`, {
            percent: Math.round(progress * 100),
          })}
          <span className="bg-chip h-1 w-12 overflow-hidden rounded-full">
            <span
              className="bg-amber block h-full"
              style={{ width: `${progress * 100}%` }}
            />
          </span>
        </span>
      ) : project[`${slot}_id`] ? (
        <span className={cn(pill, "text-ink-2 pr-1.5")}>
          <button
            type="button"
            aria-label={t(`portfolio.media.replace.${slot}`, { name })}
            onClick={() => input.current?.click()}
            className="cursor-pointer"
          >
            {label}
          </button>
          <button
            type="button"
            aria-label={t(`portfolio.media.remove.${slot}`, { name })}
            disabled={remove.isPending}
            onClick={() => remove.mutate({ projectId: project.id, slot })}
            className="text-ink-3 inline-flex size-5 cursor-pointer items-center justify-center rounded-full"
          >
            <X size={13} aria-hidden="true" />
          </button>
        </span>
      ) : (
        <button
          type="button"
          aria-label={t(`portfolio.media.choose.${slot}`, { name })}
          onClick={() => input.current?.click()}
          className={cn(pill, "text-ink-3 cursor-pointer border-dashed")}
        >
          {t(`portfolio.media.add.${slot}`)}
        </button>
      )}
      {failed && (
        <span role="alert" className="text-crit basis-full text-sm">
          {failed}
        </span>
      )}
    </>
  );
}
