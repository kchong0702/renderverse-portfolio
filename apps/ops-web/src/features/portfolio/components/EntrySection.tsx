import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { Entry, EntryKind } from "../api/profile";
import EntryTable from "./EntryTable";

interface EntrySectionProps {
  kind: EntryKind;
  entries: Entry[];
  filter?: ReactNode;
}

export default function EntrySection({
  kind,
  entries,
  filter,
}: EntrySectionProps) {
  const { t } = useTranslation();
  const headingId = `${kind}-heading`;

  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 id={headingId} className="text-ink m-0 text-base font-semibold">
            {t(`portfolio.kinds.${kind}.heading`)}
          </h2>
          <span className="text-ink-3 text-sm">
            {t(`portfolio.kinds.${kind}.description`)}
          </span>
        </div>
        {filter}
      </div>
      <EntryTable kind={kind} entries={entries} />
    </section>
  );
}
