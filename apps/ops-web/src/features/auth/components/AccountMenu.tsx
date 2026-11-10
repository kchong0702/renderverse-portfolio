import { LogOut } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useSignInMethods, useSignOut } from "../hooks/useAuth";

const footer =
  "border-side-line bg-side-foot flex w-full items-center gap-3 border-t px-[22px] py-4 text-left";

export default function AccountMenu({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { data: methods } = useSignInMethods();
  const signOut = useSignOut();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: Event) => {
      if (
        event instanceof KeyboardEvent
          ? event.key === "Escape"
          : !root.current?.contains(event.target as Node)
      )
        setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  if (!methods?.required) return <div className={footer}>{children}</div>;
  return (
    <div ref={root} className="relative">
      {open && (
        <div
          role="menu"
          aria-label={t("shell.account")}
          className="bg-side-tile border-side-on-border absolute inset-x-3 bottom-full mb-2 rounded-lg border p-1"
        >
          <button
            type="button"
            role="menuitem"
            autoFocus
            onClick={() => signOut.mutate()}
            disabled={signOut.isPending}
            className="text-side-ink hover:bg-side-foot flex w-full cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm disabled:opacity-60"
          >
            <LogOut className="text-side-muted size-4" />
            {t("shell.signOut")}
          </button>
        </div>
      )}
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className={`${footer} hover:bg-side-tile cursor-pointer`}
      >
        {children}
      </button>
    </div>
  );
}
