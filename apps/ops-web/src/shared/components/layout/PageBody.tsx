import type { ReactNode } from "react";

export default function PageBody({ children }: { children: ReactNode }) {
  return (
    <div className="px-10 pt-9 pb-16">
      <div className="mx-auto flex max-w-[1120px] flex-col gap-7">
        {children}
      </div>
    </div>
  );
}
