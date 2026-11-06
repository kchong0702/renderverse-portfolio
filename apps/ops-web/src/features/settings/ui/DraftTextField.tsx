import { useEffect, useState } from "react";
import { TextField } from "@/shared/ui/fields";

interface DraftTextFieldProps {
  label: string;
  value: string;
  placeholder?: string;
  maxLength?: number;
  onSave: (value: string) => void;
}

/** A text field that keeps what you type locally and saves it when you leave */
export default function DraftTextField({
  value,
  onSave,
  ...field
}: DraftTextFieldProps) {
  const [draft, setDraft] = useState(value);

  useEffect(() => setDraft(value), [value]);

  const save = () => {
    const next = draft.trim();
    if (next !== value) onSave(next);
  };

  return (
    <TextField
      {...field}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={save}
      onKeyDown={(event) => {
        if (event.key === "Enter") event.currentTarget.blur();
      }}
    />
  );
}
