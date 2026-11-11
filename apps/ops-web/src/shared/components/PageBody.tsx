import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

export default function PageBody({
  children,
  wide,
}: {
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="flex-1 overflow-y-auto overscroll-none px-4 pt-6 pb-16 shell:px-10 shell:pt-9">
      <div
        className={cn(
          "mx-auto flex flex-col gap-7",
          wide ? "max-w-[1600px]" : "max-w-[1120px]",
        )}
      >
        {children}
      </div>
    </div>
  );
}
