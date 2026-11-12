import { LoaderCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useActiveImports } from "../hooks/useImports";

export default function ProcessingIndicator() {
  const { t } = useTranslation();
  const count = useActiveImports().data?.length ?? 0;
  if (count === 0) return null;
  return (
    <span
      role="status"
      className="text-side-muted flex items-center gap-2 px-3 text-xs/[1.6] font-medium"
    >
      <LoaderCircle size={14} className="text-amber-soft animate-spin" />
      {t("shell.processing", { count })}
    </span>
  );
}
