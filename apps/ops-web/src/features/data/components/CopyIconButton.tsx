import { Check, Copy } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";

interface CopyIconButtonProps {
  name: string;
  copied: boolean;
  onCopy: () => void;
}

export default function CopyIconButton({
  name,
  copied,
  onCopy,
}: CopyIconButtonProps) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={onCopy}
      aria-label={t(copied ? "data.copied" : "data.copyNamed", { name })}
      title={t(copied ? "data.copied" : "data.copy")}
      className={cn(
        "inline-flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-lg",
        copied ? "text-ok" : "text-ink-3 hover:text-ink",
      )}
    >
      {copied ? <Check size={16} strokeWidth={2} /> : <Copy size={16} />}
    </button>
  );
}
