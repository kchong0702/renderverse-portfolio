import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router-dom";
import { ApiError } from "@/shared/api/http";
import { useMe } from "../hooks/useAuth";

function FullPageStatus({ children }: { children: ReactNode }) {
  return (
    <div className="text-ink-3 flex min-h-screen items-center justify-center p-4 text-sm">
      {children}
    </div>
  );
}

export default function RequireAuth({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const location = useLocation();
  const me = useMe();

  if (me.error instanceof ApiError && me.error.status === 401) {
    const next = location.pathname + location.search;
    return (
      <Navigate to={`/sign-in?${new URLSearchParams({ next })}`} replace />
    );
  }
  if (me.data) return children;
  if (me.error)
    return (
      <FullPageStatus>
        <span role="alert">
          {t("shell.loadFailed", { reason: me.error.message })}{" "}
          <button
            type="button"
            onClick={() => void me.refetch()}
            className="text-ink cursor-pointer font-semibold underline"
          >
            {t("shell.retry")}
          </button>
        </span>
      </FullPageStatus>
    );
  return (
    <FullPageStatus>
      <span role="status">{t("common.loading")}</span>
    </FullPageStatus>
  );
}
