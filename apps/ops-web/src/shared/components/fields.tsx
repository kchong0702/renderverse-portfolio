import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";

const control =
  "border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 text-sm disabled:opacity-60";

function FieldLabel({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="text-ink-3 flex flex-col gap-1.5 text-sm">
      {label}
      {children}
    </label>
  );
}

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function TextField({ label, ...input }: TextFieldProps) {
  return (
    <FieldLabel label={label}>
      <input type="text" className={control} {...input} />
    </FieldLabel>
  );
}

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
}

export function SelectField({ label, options, ...select }: SelectFieldProps) {
  return (
    <FieldLabel label={label}>
      <select className={control} {...select}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldLabel>
  );
}

interface CheckboxRowProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  note?: string;
}

export function CheckboxRow({ label, note, ...input }: CheckboxRowProps) {
  return (
    <label className="flex items-start gap-3">
      <input
        type="checkbox"
        className="accent-amber mt-[3px] size-[18px] shrink-0 disabled:opacity-60"
        {...input}
      />
      <span className="flex flex-col">
        <span className="font-medium">{label}</span>
        {note && <span className="text-ink-3 text-[13px]">{note}</span>}
      </span>
    </label>
  );
}
