import { Copy, LoaderCircle, Pencil, Sparkle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";

interface NetworkingFieldProps {
  label: string;
  text: string;
  editing: boolean;
  copied: boolean;
  sources: string | null;
  rewriting?: boolean;
  onRewrite?: () => void;
  onToggleEdit: () => void;
  onEdit: (text: string) => void;
  onCopy: () => void;
}

export default function NetworkingField({
  label,
  text,
  editing,
  copied,
  sources,
  rewriting,
  onRewrite,
  onToggleEdit,
  onEdit,
  onCopy,
}: NetworkingFieldProps) {
  const { t, i18n } = useTranslation();
  const icon =
    "text-ink-3 hover:text-ink inline-flex size-9 cursor-pointer items-center justify-center rounded-lg disabled:cursor-default disabled:opacity-60";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <span className="flex items-baseline gap-2.5">
          <span className="text-ink-2 text-[13px] font-semibold">{label}</span>
          {text && (
            <span className="text-ink-3 text-xs">
              {t("data.networking.characters", {
                count: text.length,
                formatted: new Intl.NumberFormat(i18n.language).format(
                  text.length,
                ),
              })}
            </span>
          )}
        </span>
        <span className="flex items-center gap-0.5">
          {onRewrite && (
            <button
              type="button"
              aria-label={t("data.networking.rewriteNamed", { name: label })}
              title={t("data.networking.rewrite")}
              disabled={rewriting}
              onClick={onRewrite}
              className={icon}
            >
              {rewriting ? (
                <LoaderCircle size={14} className="animate-spin" />
              ) : (
                <Sparkle size={14} />
              )}
            </button>
          )}
          <button
            type="button"
            aria-label={t("data.networking.editNamed", { name: label })}
            aria-pressed={editing}
            title={t(editing ? "data.networking.doneEditing" : "data.edit")}
            onClick={onToggleEdit}
            className={cn(icon, editing && "bg-chip text-ink")}
          >
            <Pencil size={15} />
          </button>
          <button
            type="button"
            disabled={!text}
            onClick={onCopy}
            className={cn(
              "inline-flex min-h-9 min-w-[86px] cursor-pointer items-center justify-center gap-1.5 rounded-lg px-3 text-[13px] font-semibold disabled:cursor-default disabled:opacity-45",
              copied ? "bg-ok text-white" : "bg-primary text-on-primary",
            )}
          >
            <Copy size={15} />
            {t(copied ? "data.copied" : "data.copy")}
          </button>
        </span>
      </div>
      {editing ? (
        <textarea
          aria-label={label}
          autoFocus
          rows={Math.max(2, text.split("\n").length + 1)}
          value={text}
          onChange={(event) => onEdit(event.target.value)}
          className="border-amber bg-panel text-ink resize-y rounded-[10px] border-2 px-3.5 py-3 leading-[1.7]"
        />
      ) : (
        <p
          className={cn(
            "m-0 leading-[1.7] whitespace-pre-line",
            !text && "text-ink-3",
            rewriting && "opacity-60",
          )}
        >
          {text || t("data.networking.notWritten")}
        </p>
      )}
      {sources !== null && (
        <span className="text-ink-3 text-xs">
          {t("data.networking.basedOn", { facts: sources })}
        </span>
      )}
    </div>
  );
}
