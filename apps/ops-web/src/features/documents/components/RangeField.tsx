import { useEffect, useState } from "react";

interface RangeFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (value: number) => string;
  onSave: (value: number) => void;
}

export default function RangeField({
  label,
  value,
  min,
  max,
  step,
  format,
  onSave,
}: RangeFieldProps) {
  const [draft, setDraft] = useState(value);

  useEffect(() => setDraft(value), [value]);

  const save = () => {
    if (draft !== value) onSave(draft);
  };

  return (
    <label className="text-ink-3 flex flex-col gap-1.5 text-sm">
      <span className="flex justify-between">
        {label}
        <span className="text-ink-2">{format(draft)}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={draft}
        onChange={(event) => setDraft(Number(event.target.value))}
        onPointerUp={save}
        onKeyUp={save}
        onBlur={save}
        className="accent-amber"
      />
    </label>
  );
}
