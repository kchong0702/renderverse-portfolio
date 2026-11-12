import { Pencil } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  CountryPicker,
  useUpdateProfile,
  type Preferences,
  type SalaryPeriod,
  type WorkMode,
} from "@/features/portfolio";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import Section from "./Section";

const WORK_MODES: WorkMode[] = ["onsite", "hybrid", "remote"];
const PERIODS: SalaryPeriod[] = ["month", "year", "hour"];
const control =
  "border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 text-sm";

interface PreferencesFormProps {
  preferences: Preferences;
  onDone: () => void;
}

function PreferencesForm({ preferences, onDone }: PreferencesFormProps) {
  const { t, i18n } = useTranslation();
  const update = useUpdateProfile();
  const [draft, setDraft] = useState(preferences);
  const [amount, setAmount] = useState(
    preferences.min_salary ? String(preferences.min_salary.amount) : "",
  );
  const [currency, setCurrency] = useState(
    preferences.min_salary?.currency ?? "USD",
  );
  const [period, setPeriod] = useState<SalaryPeriod>(
    preferences.min_salary?.period ?? "month",
  );
  const digits = amount.replace(/\D/g, "");
  const currencies = new Intl.DisplayNames([i18n.language], {
    type: "currency",
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    update.mutate(
      {
        preferences: {
          ...draft,
          min_salary: Number(digits)
            ? { amount: Number(digits), currency, period }
            : null,
        },
      },
      { onSuccess: onDone },
    );
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-6 pt-3">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="pref-salary" className="text-ink-3 text-sm">
          {t("data.preferences.salary")}
        </label>
        <div className="flex gap-2">
          <select
            aria-label={t("data.preferences.currency")}
            value={currency}
            onChange={(event) => setCurrency(event.target.value)}
            className={cn(control, "w-24 flex-none")}
          >
            {Intl.supportedValuesOf("currency").map((code) => (
              <option key={code} value={code} title={currencies.of(code)}>
                {code}
              </option>
            ))}
          </select>
          <input
            id="pref-salary"
            inputMode="numeric"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            className={cn(control, "min-w-0 flex-1")}
          />
          <select
            aria-label={t("data.preferences.period")}
            value={period}
            onChange={(event) => setPeriod(event.target.value as SalaryPeriod)}
            className={cn(control, "flex-none")}
          >
            {PERIODS.map((p) => (
              <option key={p} value={p}>
                {t(`data.preferences.periods.${p}`)}
              </option>
            ))}
          </select>
        </div>
        <span className="text-ink-3 text-[13px]">
          {t("data.preferences.salaryNote")}
        </span>
      </div>
      <fieldset className="m-0 flex flex-col gap-1.5 border-0 p-0">
        <legend className="text-ink-3 p-0 pb-1.5 text-sm">
          {t("data.preferences.modes")}
        </legend>
        <div className="flex flex-wrap gap-2">
          {WORK_MODES.map((mode) => {
            const on = draft.work_modes.includes(mode);
            return (
              <button
                key={mode}
                type="button"
                aria-pressed={on}
                onClick={() =>
                  setDraft({
                    ...draft,
                    work_modes: WORK_MODES.filter((m) =>
                      m === mode ? !on : draft.work_modes.includes(m),
                    ),
                  })
                }
                className={cn(
                  "min-h-10 cursor-pointer rounded-full border px-4 text-sm font-semibold",
                  on
                    ? "bg-primary text-on-primary border-primary"
                    : "bg-panel text-ink border-hair",
                )}
              >
                {t(`data.preferences.modeNames.${mode}`)}
              </button>
            );
          })}
        </div>
        <span className="text-ink-3 text-[13px]">
          {t("data.preferences.modesNote")}
        </span>
      </fieldset>
      <CountryPicker
        label={t("data.preferences.countries")}
        emptyLabel={t("data.preferences.anywhere")}
        value={draft.countries}
        onChange={(countries) => setDraft({ ...draft, countries })}
      />
      <CountryPicker
        label={t("data.preferences.visaFree")}
        emptyLabel={t("data.preferences.noneYet")}
        value={draft.authorised_countries}
        onChange={(authorised_countries) =>
          setDraft({ ...draft, authorised_countries })
        }
      />
      {update.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("data.notSaved", { reason: update.error.message })}
        </p>
      )}
      <div className="flex justify-end gap-2.5">
        <button type="button" onClick={onDone} className={buttonClass()}>
          {t("data.cancel")}
        </button>
        <button
          type="submit"
          disabled={update.isPending}
          className={buttonClass("primary")}
        >
          {update.isPending ? t("data.saving") : t("data.save")}
        </button>
      </div>
    </form>
  );
}

export default function PreferencesCard({
  preferences,
}: {
  preferences: Preferences;
}) {
  const { t, i18n } = useTranslation();
  const [editing, setEditing] = useState(false);
  const regions = new Intl.DisplayNames([i18n.language], { type: "region" });
  const list = (codes: string[]) =>
    new Intl.ListFormat(i18n.language).format(
      codes.map((code) => regions.of(code) ?? code),
    );
  const salary = preferences.min_salary;
  const amount =
    salary &&
    t("data.preferences.salaryValue", {
      currency: salary.currency,
      amount: new Intl.NumberFormat(i18n.language).format(salary.amount),
      period: t(`data.preferences.periods.${salary.period}`),
    });
  const modes = preferences.work_modes.length
    ? new Intl.ListFormat(i18n.language).format(
        preferences.work_modes.map((mode) =>
          t(`data.preferences.modeNames.${mode}`),
        ),
      )
    : null;
  const rows = [
    {
      label: t("data.preferences.salaryLabel"),
      value: amount
        ? t("data.preferences.beforeTax", { amount })
        : t("data.preferences.notSet"),
      set: Boolean(amount),
    },
    {
      label: t("data.preferences.modesLabel"),
      value: modes ?? t("data.preferences.anywhere"),
      set: true,
    },
    {
      label: t("data.preferences.countriesLabel"),
      value: preferences.countries.length
        ? list(preferences.countries)
        : t("data.preferences.anywhere"),
      set: true,
    },
    {
      label: t("data.preferences.visaFreeLabel"),
      value: preferences.authorised_countries.length
        ? list(preferences.authorised_countries)
        : t("data.preferences.noneYet"),
      set: preferences.authorised_countries.length > 0,
    },
  ];

  return (
    <Section
      title={t("data.preferences.title")}
      hint={t("data.preferences.hint")}
      summary={[amount, modes ?? t("data.preferences.anywhere")]
        .filter(Boolean)
        .join(" · ")}
    >
      <div className="flex flex-col px-4 pb-5 sm:px-[22px]">
        {editing ? (
          <PreferencesForm
            preferences={preferences}
            onDone={() => setEditing(false)}
          />
        ) : (
          <>
            <div className="flex justify-end py-3">
              <button
                type="button"
                onClick={() => setEditing(true)}
                className={cn(buttonClass(), "min-h-9")}
              >
                <Pencil size={15} />
                {t("data.edit")}
              </button>
            </div>
            <dl className="m-0 flex flex-col">
              {rows.map((row) => (
                <div
                  key={row.label}
                  className="border-hair-soft grid min-h-12 grid-cols-1 items-center gap-x-3 border-t py-2 sm:grid-cols-[180px_minmax(0,1fr)]"
                >
                  <dt className="text-ink-3 text-sm">{row.label}</dt>
                  <dd className={cn("m-0", !row.set && "text-ink-3")}>
                    {row.value}
                  </dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </div>
    </Section>
  );
}
