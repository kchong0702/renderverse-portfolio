import { useTranslation } from "react-i18next";
import Badge from "@/shared/components/Badge";
import TrashIcon from "@/shared/components/TrashIcon";
import type { Skill } from "../api/profile";
import { useDeleteSkill } from "../hooks/useProfile";

const columns =
  "grid grid-cols-[minmax(0,1fr)_40px] items-center gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_40px] sm:gap-4";

interface SkillRowProps {
  skill: Skill;
  deleteError: string | null;
  onDelete: () => void;
}

function SkillRow({ skill, deleteError, onDelete }: SkillRowProps) {
  const { t } = useTranslation();

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
        {deleteError && (
          <span role="alert" className="text-crit text-sm">
            {t("portfolio.table.deleteFailed", { reason: deleteError })}
          </span>
        )}
      </span>
      <span role="cell" className="text-ink-2 hidden text-sm sm:block">
        {skill.group}
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
          className="text-ink-3 inline-flex size-10 cursor-pointer items-center justify-center rounded-lg"
        >
          <TrashIcon />
        </button>
      </span>
    </div>
  );
}

export default function SkillsTab({ skills }: { skills: Skill[] }) {
  const { t } = useTranslation();
  const remove = useDeleteSkill();

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
        <div role="table" aria-labelledby="skills-heading">
          <div
            role="row"
            className={`${columns} border-hair text-ink-3 border-b px-5 py-3 text-[13px] font-semibold`}
          >
            <span role="columnheader">{t("portfolio.skills.name")}</span>
            <span role="columnheader" className="hidden sm:block">
              {t("portfolio.skills.group")}
            </span>
            <span role="columnheader" className="sr-only">
              {t("portfolio.table.deleteColumn")}
            </span>
          </div>
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
        </div>
        {skills.length === 0 && (
          <p className="text-ink-3 border-hair-soft m-0 border-b px-5 py-4 text-sm">
            {t("portfolio.skills.empty")}
          </p>
        )}
      </div>
    </section>
  );
}
