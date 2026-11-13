import { LoaderCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useActiveImports } from "../hooks/useImports";

export default function ProcessingIndicator({
  onClick,
}: {
  onClick: () => void;
}) {
  const { t } = useTranslation();
  const active = useActiveImports().data ?? [];
  if (active.length === 0) return null;
  return (
    <Link
      to={
        active.every((row) => row.source === "documents")
          ? "/documents/import"
          : "/data/review"
      }
      onClick={onClick}
      aria-live="polite"
      className="text-side-muted hover:text-side-ink flex min-h-11 items-center gap-2 rounded-lg px-3 text-xs/[1.6] font-medium no-underline shell:min-h-10"
    >
      <LoaderCircle size={14} className="text-amber-soft animate-spin" />
      {t("shell.processing", { count: active.length })}
    </Link>
  );
}
