import { Sparkle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useSearchParams } from "react-router-dom";
import { TextField } from "@/shared/components/ui/fields";
import ProviderButton from "../components/ui/ProviderButton";
import { useMe, useSignIn, useSignInMethods } from "../hooks/useAuth";

const callbackErrors = ["not_allowed", "failed"] as const;
type CallbackError = (typeof callbackErrors)[number];

/** Only a path on ops-web, so a link cannot send you to another site */
function safeNext(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//")) return "/";
  return next.startsWith("/sign-in") ? "/" : next;
}

export default function SignInPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const callbackError = params.get("error");

  const me = useMe();
  const methods = useSignInMethods();
  const signIn = useSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (me.data) return <Navigate to={next} replace />;

  const providers = (["google", "github"] as const).filter(
    (provider) => methods.data?.[provider],
  );
  const error = signIn.error
    ? t("auth.errors.password", { reason: signIn.error.message })
    : callbackErrors.includes(callbackError as CallbackError)
      ? t(`auth.errors.${callbackError as CallbackError}`)
      : null;

  function submit(event: FormEvent) {
    event.preventDefault();
    signIn.mutate({ email, password });
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="bg-panel border-hair shadow-card flex w-full max-w-[400px] flex-col gap-6 rounded-xl border px-[26px] py-8 sm:px-9">
        <div className="flex items-center gap-2.5">
          <span className="border-side-on-border bg-side text-amber-soft flex size-9 items-center justify-center rounded-lg border">
            <Sparkle />
          </span>
          <span className="flex flex-col">
            <span className="text-[17px] leading-tight font-bold">
              {t("shell.product")}
            </span>
            <span className="text-ink-3 text-xs">{t("shell.tagline")}</span>
          </span>
        </div>

        <div className="flex flex-col gap-1">
          <h1 className="m-0 text-xl font-semibold">{t("auth.title")}</h1>
          <p className="text-ink-3 m-0 text-sm">{t("auth.subtitle")}</p>
        </div>

        {error && (
          <p
            role="alert"
            className="border-crit/30 bg-crit-bg text-crit m-0 rounded-lg border px-3.5 py-2.5 text-sm"
          >
            {error}
          </p>
        )}

        <form onSubmit={submit} className="flex flex-col gap-4">
          <TextField
            label={t("auth.email")}
            type="email"
            name="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <TextField
            label={t("auth.password")}
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button
            type="submit"
            disabled={signIn.isPending}
            className="bg-primary text-on-primary min-h-11 cursor-pointer rounded-lg text-sm font-semibold disabled:cursor-default disabled:opacity-60"
          >
            {signIn.isPending ? t("auth.submitting") : t("auth.submit")}
          </button>
        </form>

        {providers.length > 0 && (
          <>
            <div className="text-ink-3 flex items-center gap-3 text-xs">
              <span className="bg-hair h-px flex-1" />
              {t("auth.or")}
              <span className="bg-hair h-px flex-1" />
            </div>
            <div className="flex flex-col gap-2.5">
              {providers.map((provider) => (
                <ProviderButton
                  key={provider}
                  provider={provider}
                  next={next}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
