import { useEffect, useState } from "react";
import { TextAreaField, TextField } from "@/shared/components/fields";

interface DraftTextFieldProps {
  label: string;
  value: string;
  placeholder?: string;
  maxLength?: number;
  multiline?: boolean;
  onSave: (value: string) => void;
}

export default function DraftTextField({
  value,
  onSave,
  multiline,
  ...field
}: DraftTextFieldProps) {
  const [draft, setDraft] = useState(value);

  useEffect(() => setDraft(value), [value]);

  const save = () => {
    const next = draft.trim();
    if (next !== value) onSave(next);
  };

  return multiline ? (
    <TextAreaField
      {...field}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={save}
    />
  ) : (
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
