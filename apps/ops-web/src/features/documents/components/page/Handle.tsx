import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/shared/lib/cn";

interface HandleProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: number;
  dot: number;
}

export default function Handle({
  icon,
  dot,
  className,
  ...button
}: HandleProps) {
  return (
    <button
      type="button"
      draggable
      className={cn(
        "absolute inline-flex cursor-grab items-center justify-center border-0 p-0 [zoom:var(--unzoom)]",
        className,
      )}
      {...button}
    >
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden="true"
      >
        {[9, 15].flatMap((x) =>
          [6, 12, 18].map((y) => (
            <circle key={`${x}${y}`} cx={x} cy={y} r={dot} />
          )),
        )}
      </svg>
    </button>
  );
}
