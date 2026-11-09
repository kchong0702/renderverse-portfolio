import { LogOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSignInMethods, useSignOut } from "../../hooks/useAuth";

export default function SignOutButton() {
  const { t } = useTranslation();
  const { data: methods } = useSignInMethods();
  const signOut = useSignOut();

  if (!methods?.required) return null;
  return (
    <button
      type="button"
      onClick={() => signOut.mutate()}
      disabled={signOut.isPending}
      aria-label={t("shell.signOut")}
      title={t("shell.signOut")}
      className="text-side-muted hover:text-side-ink hover:bg-side-tile flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-lg disabled:opacity-60"
    >
      <LogOut />
    </button>
  );
}
