import { cn } from "@/shared/lib/cn";
import { pillItem, pillTrack } from "./pill";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedProps<T extends string> {
  label: string;
  value: T;
  options: SegmentedOption<T>[];
  onChange: (value: T) => void;
}

export default function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: SegmentedProps<T>) {
  return (
    <div role="group" aria-label={label} className={pillTrack}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
          className={cn(
            pillItem,
            "aria-pressed:bg-panel aria-pressed:text-ink aria-pressed:shadow-card aria-pressed:font-semibold",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
