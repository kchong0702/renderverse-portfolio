import { cn } from "@/shared/lib/cn";

interface SwitchProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export default function Switch({ label, checked, onChange }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        "inline-flex h-[26px] w-11 cursor-pointer rounded-full p-[3px]",
        checked ? "bg-ok justify-end" : "bg-hair justify-start",
      )}
    >
      <span className="size-5 rounded-full bg-white shadow-[0_1px_2px_rgb(28_25_23/0.25)]" />
    </button>
  );
}
