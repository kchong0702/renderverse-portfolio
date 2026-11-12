import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";
import type { CalendarItem } from "../lib/items";

interface ItemBoxProps {
  item: CalendarItem;
  onSelect: (stepId: string) => void;
  className: string;
  style?: CSSProperties;
  children: ReactNode;
}

export default function ItemBox({
  item,
  onSelect,
  className,
  style,
  children,
}: ItemBoxProps) {
  const { stepId } = item;
  return stepId ? (
    <button
      type="button"
      className={cn(className, "cursor-pointer text-left")}
      style={style}
      onClick={() => onSelect(stepId)}
    >
      {children}
    </button>
  ) : (
    <div className={className} style={style}>
      {children}
    </div>
  );
}
