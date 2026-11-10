import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { SelectField } from "@/shared/components/fields";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

interface CountryPickerProps {
  label: string;
  emptyLabel: string;
  value: string[];
  onChange: (codes: string[]) => void;
}

export default function CountryPicker({
  label,
  emptyLabel,
  value,
  onChange,
}: CountryPickerProps) {
  const { t, i18n } = useTranslation();
  const regionNames = new Intl.DisplayNames([i18n.language], {
    type: "region",
  });
  const countries = [...LETTERS]
    .flatMap((first) => [...LETTERS].map((second) => first + second))
    .map((code) => ({ code, name: regionNames.of(code) ?? code }))
    .filter(
      ({ code, name }) =>
        name !== code && !/^(AC|CP|DG|EA|EU|EZ|IC|QO|TA|UN|ZZ)$/.test(code),
    )
    .sort((a, b) => a.name.localeCompare(b.name, i18n.language));

  return (
    <div className="flex flex-col gap-2">
      <SelectField
        label={label}
        value=""
        options={[
          { value: "", label: t("portfolio.preferences.addCountry") },
          ...countries
            .filter(({ code }) => !value.includes(code))
            .map(({ code, name }) => ({ value: code, label: name })),
        ]}
        onChange={(event) =>
          event.target.value && onChange([...value, event.target.value])
        }
      />
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        {value.length === 0 && (
          <li className="text-ink-3 text-sm">{emptyLabel}</li>
        )}
        {value.map((code) => {
          const name = regionNames.of(code) ?? code;
          return (
            <li
              key={code}
              className="bg-chip text-ink-2 flex items-center gap-1 rounded-full py-0.5 pr-1 pl-3 text-sm"
            >
              {name}
              <button
                type="button"
                aria-label={t("portfolio.preferences.removeCountry", { name })}
                onClick={() => onChange(value.filter((c) => c !== code))}
                className="text-ink-3 hover:text-ink inline-flex size-6 cursor-pointer items-center justify-center rounded-full"
              >
                <X size={14} />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
