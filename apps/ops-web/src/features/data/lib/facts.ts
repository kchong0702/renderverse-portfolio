import i18n from "@/i18n";
import type { Entry } from "@/features/portfolio";
import type { Change, FieldChange, MatchChange } from "../api/data";

export function period(start: string | null, end: string | null): string {
  const from = start?.slice(0, 4);
  const to = end === "present" ? i18n.t("data.period.now") : end?.slice(0, 4);
  return from && to && from !== to
    ? i18n.t("data.period.range", { from, to })
    : (from ?? to ?? "");
}

export const heading = (
  entry: Pick<Entry, "kind" | "title" | "organisation">,
) =>
  entry.kind === "role" && entry.organisation
    ? i18n.t("data.roleAt", {
        title: entry.title,
        organisation: entry.organisation,
      })
    : entry.title;

export const shortUrl = (url: string) =>
  url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");

export type ReviewCard =
  | { kind: "match"; key: string; change: MatchChange }
  | {
      kind: "fields";
      key: string;
      entryId: string | null;
      changes: FieldChange[];
    };

export function reviewCards(changes: Change[]): ReviewCard[] {
  const cards: ReviewCard[] = [];
  for (const change of changes) {
    if (change.kind === "match") {
      cards.push({ kind: "match", key: change.id, change });
      continue;
    }
    const key = change.entry_id ?? "about";
    const card = cards.find((c) => c.kind === "fields" && c.key === key);
    if (card?.kind === "fields") card.changes.push(change);
    else
      cards.push({
        kind: "fields",
        key,
        entryId: change.entry_id,
        changes: [change],
      });
  }
  return cards;
}
