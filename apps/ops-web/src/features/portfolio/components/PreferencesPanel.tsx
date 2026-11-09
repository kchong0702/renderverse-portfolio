import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CheckboxRow,
  SelectField,
  TextField,
} from "@/shared/components/fields";
import Panel from "@/shared/components/Panel";
import type {
  Preferences,
  ProfilePatch,
  SalaryPeriod,
  WorkMode,
} from "../api/profile";
import CountryPicker from "./CountryPicker";

const WORK_MODES: WorkMode[] = ["onsite", "hybrid", "remote"];
const PERIODS: SalaryPeriod[] = ["hour", "month", "year"];

interface PreferencesPanelProps {
  preferences: Preferences;
  onChange: (patch: ProfilePatch) => void;
}

export default function PreferencesPanel({
  preferences,
  onChange,
}: PreferencesPanelProps) {
  const { t } = useTranslation();
  const save = (change: Partial<Preferences>) =>
    onChange({ preferences: { ...preferences, ...change } });

  const salary = preferences.min_salary;
  const [amount, setAmount] = useState(salary ? String(salary.amount) : "");
  const [currency, setCurrency] = useState(salary?.currency ?? "");
  const [period, setPeriod] = useState<SalaryPeriod>(salary?.period ?? "month");
  useEffect(() => {
    setAmount(salary ? String(salary.amount) : "");
    setCurrency(salary?.currency ?? "");
    setPeriod(salary?.period ?? "month");
  }, [salary]);

  const salaryValid = /^[1-9]\d*$/.test(amount) && /^[A-Z]{3}$/.test(currency);
  const saveSalary = (nextPeriod = period) => {
    if (!amount) {
      if (salary) save({ min_salary: null });
      return;
    }
    if (!salaryValid) return;
    const next = { amount: Number(amount), currency, period: nextPeriod };
    if (
      next.amount !== salary?.amount ||
      next.currency !== salary.currency ||
      next.period !== salary.period
    )
      save({ min_salary: next });
  };

  return (
    <Panel title={t("portfolio.preferences.title")}>
      <p className="text-ink-3 m-0 -mt-2 text-sm">
        {t("portfolio.preferences.note")}
      </p>
      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="text-ink-3 mb-1.5 p-0 text-sm">
          {t("portfolio.preferences.workModes")}
        </legend>
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          {WORK_MODES.map((mode) => (
            <CheckboxRow
              key={mode}
              label={t(`portfolio.preferences.modes.${mode}`)}
              checked={preferences.work_modes.includes(mode)}
              onChange={(event) =>
                save({
                  work_modes: WORK_MODES.filter((m) =>
                    m === mode
                      ? event.target.checked
                      : preferences.work_modes.includes(m),
                  ),
                })
              }
            />
          ))}
        </div>
        <span className="text-ink-3 text-[13px]">
          {t("portfolio.preferences.anyMode")}
        </span>
      </fieldset>
      <CountryPicker
        label={t("portfolio.preferences.countries")}
        emptyLabel={t("portfolio.preferences.anyCountry")}
        value={preferences.countries}
        onChange={(countries) => save({ countries })}
      />
      <CountryPicker
        label={t("portfolio.preferences.authorisedCountries")}
        emptyLabel={t("portfolio.preferences.noCountry")}
        value={preferences.authorised_countries}
        onChange={(authorised_countries) => save({ authorised_countries })}
      />
      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="text-ink-3 mb-1.5 p-0 text-sm">
          {t("portfolio.preferences.minSalary")}
        </legend>
        <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)] gap-3.5">
          <TextField
            label={t("portfolio.preferences.amount")}
            inputMode="numeric"
            value={amount}
            onChange={(event) => setAmount(event.target.value.trim())}
            onBlur={() => saveSalary()}
          />
          <TextField
            label={t("portfolio.preferences.currency")}
            placeholder={t("portfolio.preferences.currencyPlaceholder")}
            maxLength={3}
            value={currency}
            onChange={(event) =>
              setCurrency(event.target.value.trim().toUpperCase())
            }
            onBlur={() => saveSalary()}
          />
          <SelectField
            label={t("portfolio.preferences.period")}
            options={PERIODS.map((p) => ({
              value: p,
              label: t(`portfolio.preferences.periods.${p}`),
            }))}
            value={period}
            onChange={(event) => {
              const next = event.target.value as SalaryPeriod;
              setPeriod(next);
              saveSalary(next);
            }}
          />
        </div>
        {amount && !salaryValid && (
          <span className="text-warn text-[13px]">
            {t("portfolio.preferences.salaryIncomplete")}
          </span>
        )}
      </fieldset>
    </Panel>
  );
}
