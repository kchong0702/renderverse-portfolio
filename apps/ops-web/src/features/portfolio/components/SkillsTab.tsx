import { Trash2 } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import Badge from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import { TextField } from "@/shared/components/fields";
import type { Skill } from "../api/profile";
import { useAddSkill, useDeleteSkill, useSaveSkill } from "../hooks/useProfile";
import Switch from "./Switch";

const columns =
  "grid grid-cols-[minmax(0,1fr)_64px_40px] items-center gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_120px_40px] sm:gap-4";

interface SkillRowProps {
  skill: Skill;
  deleteError: string | null;
  onDelete: () => void;
}

function SkillRow({ skill, deleteError, onDelete }: SkillRowProps) {
  const { t } = useTranslation();
  const toggle = useSaveSkill();

  return (
    <div
      role="row"
      className={`${columns} border-hair-soft border-b px-5 py-3 ${skill.archived ? "opacity-70" : ""}`}
    >
      <span role="cell" className="flex min-w-0 flex-col">
        <span className="flex flex-wrap items-center gap-2.5 font-semibold">
          {skill.name}
          {skill.archived && <Badge>{t("portfolio.table.archived")}</Badge>}
        </span>
        <span className="text-ink-3 text-[13px] sm:hidden">{skill.group}</span>
        {toggle.isError && (
          <span role="alert" className="text-crit text-sm">
            {t("portfolio.table.toggleFailed", {
              reason: toggle.error.message,
            })}
          </span>
        )}
        {deleteError && (
          <span role="alert" className="text-crit text-sm">
            {t("portfolio.table.deleteFailed", { reason: deleteError })}
          </span>
        )}
      </span>
      <span role="cell" className="text-ink-2 hidden text-sm sm:block">
        {skill.group}
      </span>
      <span role="cell" className="flex justify-center">
        <Switch
          label={t("portfolio.table.useInAgent", { name: skill.name })}
          checked={!skill.archived}
          onChange={(on) => toggle.mutate({ ...skill, archived: !on })}
        />
      </span>
      <span role="cell" className="flex justify-end">
        <button
          type="button"
          aria-label={t("portfolio.table.delete", { name: skill.name })}
          onClick={() => {
            if (
              window.confirm(
                t("portfolio.table.confirmDelete", { name: skill.name }),
              )
            )
              onDelete();
          }}
          className="text-ink-3 hover:text-crit inline-flex size-10 cursor-pointer items-center justify-center rounded-lg"
        >
          <Trash2 size={18} />
        </button>
      </span>
    </div>
  );
}

export default function SkillsTab({ skills }: { skills: Skill[] }) {
  const { t } = useTranslation();
  const add = useAddSkill();
  const remove = useDeleteSkill();
  const [name, setName] = useState("");
  const [group, setGroup] = useState("");
  const groupsId = useId();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    add.mutate(
      { name: name.trim(), group: group.trim(), archived: false },
      { onSuccess: () => setName("") },
    );
  };

  return (
    <section aria-labelledby="skills-heading" className="flex flex-col gap-4">
      <div className="flex flex-col gap-0.5">
        <h2
          id="skills-heading"
          className="text-ink m-0 text-base font-semibold"
        >
          {t("portfolio.skills.heading")}
        </h2>
        <span className="text-ink-3 text-sm">
          {t("portfolio.skills.description")}
        </span>
      </div>
      <div className="bg-panel border-hair shadow-card overflow-hidden rounded-xl border">
        <div
          role="row"
          className={`${columns} border-hair text-ink-3 border-b px-5 py-3 text-[13px] font-semibold`}
        >
          <span role="columnheader">{t("portfolio.skills.name")}</span>
          <span role="columnheader" className="hidden sm:block">
            {t("portfolio.skills.group")}
          </span>
          <span role="columnheader" className="text-center">
            {t("portfolio.table.agentContext")}
          </span>
          <span role="columnheader" className="sr-only">
            {t("portfolio.table.deleteColumn")}
          </span>
        </div>
        {skills.length === 0 && (
          <p className="text-ink-3 border-hair-soft m-0 border-b px-5 py-4 text-sm">
            {t("portfolio.skills.empty")}
          </p>
        )}
        {skills.map((skill) => (
          <SkillRow
            key={skill.id}
            skill={skill}
            deleteError={
              remove.isError && remove.variables === skill.id
                ? remove.error.message
                : null
            }
            onDelete={() => remove.mutate(skill.id)}
          />
        ))}
        <form
          onSubmit={submit}
          className="flex flex-wrap items-end gap-3.5 px-5 py-4"
        >
          <div className="min-w-[180px] flex-1">
            <TextField
              label={t("portfolio.skills.name")}
              placeholder={t("portfolio.skills.namePlaceholder")}
              required
              maxLength={100}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="min-w-[180px] flex-1">
            <TextField
              label={t("portfolio.skills.group")}
              placeholder={t("portfolio.skills.groupPlaceholder")}
              maxLength={100}
              list={groupsId}
              value={group}
              onChange={(event) => setGroup(event.target.value)}
            />
            <datalist id={groupsId}>
              {[...new Set(skills.map((skill) => skill.group))]
                .filter(Boolean)
                .map((g) => (
                  <option key={g} value={g} />
                ))}
            </datalist>
          </div>
          <button
            type="submit"
            disabled={add.isPending}
            className={buttonClass("primary")}
          >
            {t("portfolio.skills.add")}
          </button>
        </form>
        {add.isError && (
          <p role="alert" className="text-crit m-0 px-5 pb-4 text-sm">
            {t("portfolio.form.failed", { reason: add.error.message })}
          </p>
        )}
      </div>
    </section>
  );
}
