import { Check, ChevronLeft } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { ImportRecord } from "@/features/imports";
import { useEntries, type Entry, type EntryKind } from "@/features/portfolio";
import Badge from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import StateMessage from "@/shared/components/StateMessage";
import { dayMonth } from "@/shared/lib/dates";
import { cn } from "@/shared/lib/cn";
import type { ChangeField, FieldValue, ImportedEntry } from "../api/data";
import { useChanges, useImports, useResolveChanges } from "../hooks/useData";
import { heading, period, reviewCards, type ReviewCard } from "../lib/facts";

interface CardHeadProps {
  kind: EntryKind | "about";
  title: string;
  sources: string[];
  unsure?: boolean;
}

function CardHead({ kind, title, sources, unsure }: CardHeadProps) {
  const { t } = useTranslation();
  return (
    <div className="border-hair-soft flex flex-wrap items-center gap-x-3 gap-y-2 border-b px-4 py-4 sm:px-5">
      <Badge>{t(`data.review.kinds.${kind}`)}</Badge>
      <h2 className="m-0 flex-[1_1_240px] text-base font-semibold">{title}</h2>
      {unsure && <Badge tone="warn">{t("data.review.unsure")}</Badge>}
      <span className="text-ink-3 flex basis-full flex-wrap gap-x-3.5 gap-y-1 text-[13px]">
        {sources.map((source) => (
          <span key={source}>{t("data.review.source", { source })}</span>
        ))}
      </span>
    </div>
  );
}

function FieldCard({
  card,
  entry,
  sources,
}: {
  card: Extract<ReviewCard, { kind: "fields" }>;
  entry: Entry | undefined;
  sources: string[];
}) {
  const { t, i18n } = useTranslation();
  const resolve = useResolveChanges();
  const [picks, setPicks] = useState<Record<string, "current" | "conflict">>(
    {},
  );
  const show = (field: ChangeField, value: FieldValue) => {
    if (Array.isArray(value))
      return field === "highlights"
        ? value.map((line) => `• ${line}`).join("\n")
        : value.join(", ");
    if (value === "present") return t("data.period.now");
    if ((field === "start" || field === "end") && value)
      return value.length === 4
        ? value
        : new Intl.DateTimeFormat(i18n.language, {
            month: "short",
            year: "numeric",
          }).format(new Date(`${value}-01T00:00`));
    return value ?? "";
  };
  const save = (all?: "current") =>
    resolve.mutate(
      card.changes.map((change) => ({
        id: change.id,
        choice: all ?? picks[change.id] ?? "current",
      })),
    );

  return (
    <article className="bg-panel border-hair shadow-card flex flex-col rounded-xl border">
      <CardHead
        kind={entry?.kind ?? "about"}
        title={
          card.entryId === null
            ? t("data.review.aboutTitle")
            : entry
              ? heading(entry)
              : t("data.review.missing")
        }
        sources={sources}
      />
      <div className="flex flex-col px-4 pt-2 pb-1 sm:px-5">
        <div
          aria-hidden="true"
          className="text-ink-3 grid grid-cols-2 gap-3 py-2 text-[13px] font-semibold sm:grid-cols-[120px_minmax(0,1fr)_minmax(0,1fr)]"
        >
          <span className="hidden sm:block">{t("data.review.field")}</span>
          <span>{t("data.review.current")}</span>
          <span>{t("data.review.conflict")}</span>
        </div>
        {card.changes.map((change) => {
          const label = t(`data.review.fields.${change.field}`);
          return (
            <div
              key={change.id}
              role="group"
              aria-label={label}
              className="border-hair-soft grid grid-cols-2 gap-x-3 gap-y-1.5 border-t py-2.5 sm:grid-cols-[120px_minmax(0,1fr)_minmax(0,1fr)]"
            >
              <span className="col-span-2 text-sm font-semibold sm:col-span-1 sm:pt-2.5">
                {label}
              </span>
              {(["current", "conflict"] as const).map((side) => {
                const value = show(change.field, change[side]);
                const on = (picks[change.id] ?? "current") === side;
                return (
                  <button
                    key={side}
                    type="button"
                    aria-pressed={on}
                    aria-label={t(`data.review.keep.${side}`, {
                      value: value || t("data.review.empty"),
                    })}
                    onClick={() => setPicks({ ...picks, [change.id]: side })}
                    className={cn(
                      "text-ink flex cursor-pointer items-start rounded-[10px] px-3 py-2.5 text-left text-sm leading-[1.55] [overflow-wrap:anywhere] whitespace-pre-line",
                      on
                        ? "bg-warn-bg border-amber border-2"
                        : "border-hair border",
                    )}
                  >
                    {value || (
                      <span className="text-ink-3 italic">
                        {t("data.review.empty")}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
      {resolve.isError && (
        <p role="alert" className="text-crit m-0 px-4 text-sm sm:px-5">
          {t("data.notSaved", { reason: resolve.error.message })}
        </p>
      )}
      <div className="flex flex-wrap items-center justify-end gap-2.5 px-4 pt-3 pb-4 sm:px-5">
        <button
          type="button"
          disabled={resolve.isPending}
          onClick={() => save("current")}
          className={buttonClass()}
        >
          {t("data.review.keepAll")}
        </button>
        <button
          type="button"
          disabled={resolve.isPending}
          onClick={() => save()}
          className={buttonClass("primary")}
        >
          {resolve.isPending ? t("data.saving") : t("data.review.save")}
        </button>
      </div>
    </article>
  );
}

function MatchCard({
  card,
  entry,
  sources,
}: {
  card: Extract<ReviewCard, { kind: "match" }>;
  entry: Entry | undefined;
  sources: string[];
}) {
  const { t } = useTranslation();
  const resolve = useResolveChanges();
  const imported = card.change.entry;
  const sides: {
    key: "current" | "conflict";
    entry: Pick<ImportedEntry, "title" | "organisation" | "start" | "end">;
  }[] = [
    ...(entry ? [{ key: "current" as const, entry }] : []),
    { key: "conflict", entry: imported },
  ];
  const answer = (choice: "same" | "different") =>
    resolve.mutate([{ id: card.change.id, choice }]);

  return (
    <article className="bg-panel border-hair shadow-card flex flex-col rounded-xl border">
      <CardHead
        kind={imported.kind}
        title={heading(imported)}
        sources={sources}
        unsure
      />
      <div className="flex flex-col gap-3.5 px-4 py-4 sm:px-5">
        <span className="text-ink-2 text-sm">
          {t(`data.review.match.question.${imported.kind}`)}
        </span>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(240px,100%),1fr))] gap-3">
          {sides.map((side) => (
            <div key={side.key} className="flex flex-col gap-0.5">
              <span className="text-ink-3 text-xs font-semibold">
                {t(`data.review.${side.key}`)}
              </span>
              <span className="font-semibold">{side.entry.title}</span>
              <span className="text-ink-2 text-sm">
                {[
                  side.entry.organisation,
                  period(side.entry.start, side.entry.end),
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </div>
          ))}
        </div>
        {resolve.isError && (
          <p role="alert" className="text-crit m-0 text-sm">
            {t("data.notSaved", { reason: resolve.error.message })}
          </p>
        )}
        <div className="flex flex-wrap gap-2.5">
          <button
            type="button"
            disabled={resolve.isPending}
            onClick={() => answer("same")}
            className={buttonClass("primary")}
          >
            {t(`data.review.match.same.${imported.kind}`)}
          </button>
          <button
            type="button"
            disabled={resolve.isPending}
            onClick={() => answer("different")}
            className={buttonClass()}
          >
            {t(`data.review.match.different.${imported.kind}`)}
          </button>
        </div>
      </div>
    </article>
  );
}

export default function ReviewPage() {
  const { t, i18n } = useTranslation();
  const changes = useChanges();
  const entries = useEntries();
  const imports = useImports();
  const cards = changes.data ? reviewCards(changes.data) : [];
  const failed = [changes, entries, imports].find((query) => query.isError);
  const label = (row: ImportRecord) =>
    `${row.filename}, ${dayMonth(new Date(row.created_at), i18n.language)}`;
  const sourcesOf = (ids: string[]) =>
    [...new Set(ids)].map((id) => {
      const row = imports.data?.find((item) => item.id === id);
      return row ? label(row) : t("data.review.earlierImport");
    });

  return (
    <>
      <header className="bg-header border-hair flex min-h-16 flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b px-4 py-3.5 shell:px-10">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3.5 gap-y-1.5">
          <Link
            to="/data"
            className="text-ink-3 inline-flex min-h-10 items-center gap-1 text-sm font-semibold no-underline"
          >
            <ChevronLeft size={15} />
            {t("data.title")}
          </Link>
          <h1 className="m-0 text-xl font-semibold">
            {t("data.review.title")}
          </h1>
          <span className="text-ink-3 text-sm">
            {t("data.review.subtitle")}
          </span>
        </div>
        {changes.data && (
          <span role="status" className="text-ink-2 text-sm font-semibold">
            {cards.length
              ? t("data.review.waitingCount", { count: cards.length })
              : t("data.review.allDone")}
          </span>
        )}
      </header>
      <PageBody>
        {failed?.error ? (
          <StateMessage tone="error">
            {t("data.review.loadFailed", { reason: failed.error.message })}
          </StateMessage>
        ) : !changes.data || !entries.data || !imports.data ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : (
          <div className="flex flex-wrap items-start gap-6">
            <section
              aria-label={t("data.review.listLabel")}
              className="flex min-w-0 flex-[999_1_600px] flex-col gap-4"
            >
              {cards.length === 0 ? (
                <div className="bg-panel border-hair shadow-card flex flex-col items-start gap-3 rounded-xl border px-5 py-6">
                  <span className="flex items-center gap-2.5 font-semibold">
                    <span className="bg-ok flex size-5 items-center justify-center rounded-full text-white">
                      <Check size={12} strokeWidth={3} />
                    </span>
                    {t("data.review.emptyTitle")}
                  </span>
                  <span className="text-ink-2 text-sm">
                    {t("data.review.emptyText")}
                  </span>
                  <Link to="/data" className={buttonClass()}>
                    {t("data.review.back")}
                  </Link>
                </div>
              ) : (
                <>
                  <p className="text-ink-2 m-0 text-sm">
                    {t("data.review.intro")}
                  </p>
                  {cards.map((card) =>
                    card.kind === "match" ? (
                      <MatchCard
                        key={card.key}
                        card={card}
                        entry={entries.data.find(
                          (e) => e.id === card.change.entry_id,
                        )}
                        sources={sourcesOf([card.change.import_id])}
                      />
                    ) : (
                      <FieldCard
                        key={card.key}
                        card={card}
                        entry={entries.data.find((e) => e.id === card.entryId)}
                        sources={sourcesOf(
                          card.changes.map((change) => change.import_id),
                        )}
                      />
                    ),
                  )}
                </>
              )}
            </section>
            <aside
              aria-labelledby="waiting-heading"
              className="bg-panel border-hair shadow-card flex flex-[1_1_260px] flex-col gap-3.5 rounded-xl border px-5 py-[18px]"
            >
              <div className="border-hair-soft flex items-baseline justify-between gap-3 border-b pb-3">
                <h2
                  id="waiting-heading"
                  className="m-0 text-[15px] font-semibold"
                >
                  {t("data.review.waiting")}
                </h2>
                <span
                  className={cn(
                    "text-[22px] font-semibold",
                    cards.length ? "text-warn" : "text-ok",
                  )}
                >
                  {cards.length}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-ink-3 text-[13px] font-semibold">
                  {t("data.review.imports")}
                </span>
                {imports.data.every((row) => row.status !== "done") && (
                  <span className="text-ink-3 py-2 text-[13px]">
                    {t("data.review.noImports")}
                  </span>
                )}
                {imports.data
                  .filter((row) => row.status === "done")
                  .map((row) => (
                    <div
                      key={row.id}
                      className="border-hair-soft flex flex-col gap-0.5 border-b py-2"
                    >
                      <span className="text-sm font-semibold [overflow-wrap:anywhere]">
                        {row.filename}
                      </span>
                      <span className="text-ink-3 text-[13px]">
                        {[
                          dayMonth(new Date(row.created_at), i18n.language),
                          t(`data.review.sources.${row.source}`),
                          t("data.review.added", { count: row.added }),
                          t("data.review.conflicts", { count: row.conflicts }),
                        ].join(" · ")}
                      </span>
                    </div>
                  ))}
              </div>
              <div className="flex flex-col gap-1.5">
                <span className="text-ink-3 text-[13px] font-semibold">
                  {t("data.review.rulesTitle")}
                </span>
                <ul className="text-ink-2 m-0 flex list-disc flex-col gap-1 pl-4 text-[13px]">
                  {(["one", "match", "same"] as const).map((rule) => (
                    <li key={rule}>{t(`data.review.rules.${rule}`)}</li>
                  ))}
                </ul>
              </div>
            </aside>
          </div>
        )}
      </PageBody>
    </>
  );
}
