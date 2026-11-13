import { Copy, Sparkle } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Entry, Skill } from "@/features/portfolio";
import { buttonClass } from "@/shared/components/button";
import { CheckboxRow } from "@/shared/components/fields";
import StateMessage from "@/shared/components/StateMessage";
import { cn } from "@/shared/lib/cn";
import { useCopied } from "../hooks/useCopied";
import { useNetworking, useWriteNetworking } from "../hooks/useData";
import { heading, period } from "../lib/facts";
import NetworkingField from "./NetworkingField";
import Section from "./Section";

interface NetworkingTabProps {
  entries: Entry[];
  skills: Skill[];
}

export default function NetworkingTab({ entries, skills }: NetworkingTabProps) {
  const { t, i18n } = useTranslation();
  const networking = useNetworking();
  const write = useWriteNetworking();
  const [profession, setProfession] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<string | null>(null);
  const [sources, setSources] = useState(false);
  const { copied, copy } = useCopied();

  if (networking.isError)
    return (
      <StateMessage tone="error">
        {t("data.networking.loadFailed", { reason: networking.error.message })}
      </StateMessage>
    );
  if (!networking.data)
    return <StateMessage>{t("common.loading")}</StateMessage>;

  const copyText = networking.data;
  const roles = entries.filter((entry) => entry.kind === "role");
  const names = new Map<string, string>([
    ["about", t("data.networking.facts.about")],
    ...entries.map((entry): [string, string] => [
      `${entry.kind}-${entry.id}`,
      entry.kind === "role" && entry.organisation
        ? t("data.networking.facts.role", { organisation: entry.organisation })
        : entry.title,
    ]),
    ...skills.map((skill): [string, string] => [
      `skill-${skill.id}`,
      skill.name,
    ]),
  ]);
  const writing = write.isPending && write.variables.only === null;
  const rewrite = (only: string | null) =>
    write.mutate(
      { profession: (profession ?? copyText.profession).trim(), only },
      {
        onSuccess: () =>
          setEdits((current) =>
            only
              ? Object.fromEntries(
                  Object.entries(current).filter(([key]) => key !== only),
                )
              : {},
          ),
      },
    );
  const field = (
    key: string,
    label: string,
    text: string,
    facts: string[],
    canRewrite = true,
  ) => (
    <NetworkingField
      label={label}
      text={edits[key] ?? text}
      editing={editing === key}
      copied={copied === key}
      sources={
        sources && facts.length
          ? new Intl.ListFormat(i18n.language).format(
              facts.map((fact) => names.get(fact) ?? fact),
            )
          : null
      }
      rewriting={writing || (write.isPending && write.variables.only === key)}
      onRewrite={canRewrite ? () => rewrite(key) : undefined}
      onToggleEdit={() => setEditing(editing === key ? null : key)}
      onEdit={(value) => setEdits({ ...edits, [key]: value })}
      onCopy={() => copy(key, edits[key] ?? text)}
    />
  );
  const characters = (text: string | undefined) =>
    text
      ? t("data.networking.characters", {
          count: text.length,
          formatted: new Intl.NumberFormat(i18n.language).format(text.length),
        })
      : t("data.networking.notWritten");
  const written = Boolean(
    copyText.headline || copyText.summary || copyText.descriptions.length,
  );

  return (
    <div className="flex flex-col gap-5">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          rewrite(null);
        }}
        className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2.5"
      >
        <label className="flex flex-[1_1_380px] flex-wrap items-center gap-x-3 gap-y-1.5">
          <span className="text-ink-3 text-sm">
            {t("data.networking.profession")}
          </span>
          <input
            maxLength={200}
            placeholder={t("data.networking.professionPlaceholder")}
            value={profession ?? copyText.profession}
            onChange={(event) => setProfession(event.target.value)}
            className="border-hair text-ink placeholder:text-ink-3 min-h-10 flex-[1_1_260px] border-0 border-b bg-transparent px-0.5 text-base font-semibold placeholder:font-normal"
          />
        </label>
        <button
          type="submit"
          disabled={write.isPending}
          className={buttonClass("primary")}
        >
          <Sparkle size={14} className="text-amber-soft" />
          {writing
            ? t("data.networking.writing")
            : written
              ? t("data.networking.writeAgain")
              : t("data.networking.write")}
        </button>
      </form>
      {write.isError && (
        <StateMessage tone="error">
          {t("data.networking.writeFailed", { reason: write.error.message })}
        </StateMessage>
      )}
      <Section
        title={t("data.networking.headline.title")}
        hint={t("data.networking.headline.hint")}
        summary={characters(copyText.headline?.text)}
        defaultOpen
      >
        <div className="px-4 pt-3 pb-5 sm:px-[22px]">
          {field(
            "headline",
            t("data.networking.toPaste"),
            copyText.headline?.text ?? "",
            copyText.headline?.facts ?? [],
          )}
        </div>
      </Section>
      <Section
        title={t("data.networking.summary.title")}
        hint={t("data.networking.summary.hint")}
        summary={characters(copyText.summary?.text)}
      >
        <div className="px-4 pt-3 pb-5 sm:px-[22px]">
          {field(
            "summary",
            t("data.networking.toPaste"),
            copyText.summary?.text ?? "",
            copyText.summary?.facts ?? [],
          )}
        </div>
      </Section>
      <Section
        title={t("data.networking.experience.title")}
        hint={t("data.networking.experience.hint")}
        summary={t("data.entries.role.count", { count: roles.length })}
      >
        <div className="flex flex-col px-4 pb-5 sm:px-[22px]">
          {roles.length === 0 && (
            <p className="text-ink-3 m-0 pt-3 text-sm">
              {t("data.entries.role.empty")}
            </p>
          )}
          {roles.map((role, index) => {
            const fact = `role-${role.id}`;
            const description = copyText.descriptions.find(
              (d) => d.fact === fact,
            );
            const when = period(role.start, role.end);
            return (
              <div
                key={role.id}
                className={cn(
                  "flex flex-col gap-4 pt-4",
                  index > 0 && "border-hair mt-5 border-t pt-5",
                )}
              >
                <span className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
                  <span className="font-semibold">{heading(role)}</span>
                  <span className="text-ink-3 text-[13px]">
                    {role.archived
                      ? t("data.networking.offRole", { when })
                      : when}
                  </span>
                </span>
                {field(
                  `title-${role.id}`,
                  t("data.networking.jobTitle"),
                  role.title,
                  [fact],
                  false,
                )}
                {field(
                  fact,
                  t("data.networking.description"),
                  description?.text ?? "",
                  description?.facts ?? [],
                )}
              </div>
            );
          })}
        </div>
      </Section>
      <Section
        title={t("data.networking.skills.title")}
        hint={t("data.networking.skills.hint")}
        summary={t("data.skills.count", { count: skills.length })}
      >
        <div className="flex flex-col gap-3 px-4 pt-3 pb-5 sm:px-[22px]">
          <div className="flex justify-end">
            <button
              type="button"
              disabled={skills.length === 0}
              onClick={() =>
                copy("skills", skills.map((skill) => skill.name).join(", "))
              }
              className={cn(
                "inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-[13px] font-semibold disabled:cursor-default disabled:opacity-45",
                copied === "skills"
                  ? "bg-ok text-white"
                  : "bg-primary text-on-primary",
              )}
            >
              <Copy size={15} />
              {t(copied === "skills" ? "data.copied" : "data.copyAll")}
            </button>
          </div>
          {skills.length === 0 ? (
            <p className="text-ink-3 m-0 text-sm">{t("data.skills.empty")}</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <button
                  key={skill.id}
                  type="button"
                  aria-label={t(
                    copied === skill.id ? "data.copied" : "data.copyNamed",
                    { name: skill.name },
                  )}
                  title={t("data.copy")}
                  onClick={() => copy(skill.id, skill.name)}
                  className={cn(
                    "text-ink min-h-[34px] cursor-pointer rounded-full border px-3 text-sm",
                    copied === skill.id
                      ? "border-ok bg-ok-bg"
                      : "border-hair bg-panel",
                  )}
                >
                  {skill.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </Section>
      <div className="min-h-10 content-center">
        <CheckboxRow
          label={t("data.networking.showSources")}
          checked={sources}
          onChange={(event) => setSources(event.target.checked)}
        />
      </div>
    </div>
  );
}
