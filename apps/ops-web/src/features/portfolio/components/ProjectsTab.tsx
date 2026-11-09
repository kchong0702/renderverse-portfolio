import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import Segmented from "@/shared/components/Segmented";
import type { Entry } from "../api/profile";
import EntrySection from "./EntrySection";

type Show = "active" | "archived";

export default function ProjectsTab({ entries }: { entries: Entry[] }) {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const show: Show = params.get("show") === "archived" ? "archived" : "active";
  const projects = entries.filter((entry) => entry.kind === "project");
  const count = (archived: boolean) =>
    projects.filter((project) => project.archived === archived).length;

  return (
    <EntrySection
      kind="project"
      entries={projects.filter(
        (project) => project.archived === (show === "archived"),
      )}
      filter={
        <Segmented<Show>
          label={t("portfolio.filters.label")}
          value={show}
          options={[
            {
              value: "active",
              label: t("portfolio.filters.active", { count: count(false) }),
            },
            {
              value: "archived",
              label: t("portfolio.filters.archived", { count: count(true) }),
            },
          ]}
          onChange={(next) =>
            setParams(
              (current) => {
                const updated = new URLSearchParams(current);
                updated.set("show", next);
                return updated;
              },
              { replace: true },
            )
          }
        />
      }
    />
  );
}
