import { useId, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useAddSkill, useSaveSkill, type Skill } from "@/features/portfolio";
import { buttonClass } from "@/shared/components/button";
import { TextField } from "@/shared/components/fields";
import { cn } from "@/shared/lib/cn";
import Section from "./Section";

function SkillForm({
  skills,
  onDone,
}: {
  skills: Skill[];
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const add = useAddSkill();
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
    <form onSubmit={submit} className="flex flex-col gap-3.5">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(200px,100%),1fr))] gap-3.5">
        <TextField
          label={t("data.skills.name")}
          placeholder={t("data.skills.namePlaceholder")}
          autoFocus
          required
          maxLength={100}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <TextField
          label={t("data.skills.group")}
          placeholder={t("data.skills.groupPlaceholder")}
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
      {add.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("data.notSaved", { reason: add.error.message })}
        </p>
      )}
      <div className="flex justify-end gap-2.5">
        <button type="button" onClick={onDone} className={buttonClass()}>
          {t("data.skills.done")}
        </button>
        <button
          type="submit"
          disabled={add.isPending}
          className={buttonClass("primary")}
        >
          {t("data.skills.add")}
        </button>
      </div>
    </form>
  );
}

export default function SkillsCard({ skills }: { skills: Skill[] }) {
  const { t } = useTranslation();
  const [adding, setAdding] = useState(false);
  const toggle = useSaveSkill();
  const off = skills.filter((skill) => skill.archived).length;

  return (
    <Section
      title={t("data.skills.title")}
      hint={t("data.skills.hint")}
      summary={[
        t("data.skills.count", { count: skills.length }),
        off ? t("data.entries.offCount", { count: off }) : "",
      ]
        .filter(Boolean)
        .join(" · ")}
    >
      <div className="flex flex-col gap-3.5 px-4 pt-3 pb-5 sm:px-[22px]">
        {adding ? (
          <SkillForm skills={skills} onDone={() => setAdding(false)} />
        ) : (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setAdding(true)}
              className={cn(buttonClass(), "min-h-9")}
            >
              {t("data.skills.addButton")}
            </button>
          </div>
        )}
        {skills.length === 0 ? (
          <p className="text-ink-3 m-0 text-sm">{t("data.skills.empty")}</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {skills.map((skill) => (
              <button
                key={skill.id}
                type="button"
                aria-pressed={!skill.archived}
                title={t(
                  skill.archived ? "data.skills.turnOn" : "data.skills.turnOff",
                )}
                onClick={() =>
                  toggle.mutate({ ...skill, archived: !skill.archived })
                }
                className={cn(
                  "min-h-[34px] cursor-pointer rounded-full border px-3 text-sm",
                  skill.archived
                    ? "border-ink-3 text-ink-3 border-dashed line-through"
                    : "border-hair bg-panel text-ink",
                )}
              >
                {skill.name}
              </button>
            ))}
          </div>
        )}
        {toggle.isError && (
          <p role="alert" className="text-crit m-0 text-sm">
            {t("data.notSaved", { reason: toggle.error.message })}
          </p>
        )}
      </div>
    </Section>
  );
}
