import { Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useJobs } from "@/features/jobs";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import Panel from "@/shared/components/Panel";
import Segmented from "@/shared/components/Segmented";
import StateMessage from "@/shared/components/StateMessage";
import ApplicationBoard from "../components/ApplicationBoard";
import ApplicationForm from "../components/ApplicationForm";
import ApplicationTable from "../components/ApplicationTable";
import {
  useAddApplication,
  useApplications,
  useDeleteApplication,
  useSaveApplication,
} from "../hooks/useApplications";
import { isDue } from "../lib/stages";

const VIEWS = ["board", "table"] as const;
type View = (typeof VIEWS)[number];

export default function ApplicationsPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const applications = useApplications();
  const jobs = useJobs();
  const add = useAddApplication();
  const save = useSaveApplication();
  const remove = useDeleteApplication();
  const view: View =
    VIEWS.find((name) => name === params.get("view")) ?? "board";
  const editing = params.get("edit");
  const edited = applications.data?.find((a) => a.id === editing);
  const fromJob = jobs.data?.find((job) => job.id === params.get("job"));
  const active = applications.data?.filter((a) => a.stage !== "closed") ?? [];

  const setEditing = (id: string | null) =>
    setParams(id ? { view, edit: id } : { view }, { replace: true });

  return (
    <>
      <PageHeader
        title={t("applications.title")}
        subtitle={
          applications.data &&
          t("applications.subtitle", {
            active: active.length,
            due: active.filter(isDue).length,
          })
        }
        actions={
          <>
            <Segmented
              label={t("applications.views.label")}
              value={view}
              options={VIEWS.map((name) => ({
                value: name,
                label: t(`applications.views.${name}`),
              }))}
              onChange={(next) =>
                setParams(
                  editing ? { view: next, edit: editing } : { view: next },
                )
              }
            />
            <button
              type="button"
              className={buttonClass("primary")}
              onClick={() => setEditing("new")}
            >
              <Plus size={14} className="text-amber-soft" />
              {t("applications.track")}
            </button>
          </>
        }
      />
      <PageBody>
        {applications.isError ? (
          <StateMessage tone="error">
            {t("applications.loadFailed", {
              reason: applications.error.message,
            })}
          </StateMessage>
        ) : !applications.data ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : (
          <>
            {editing === "new" && (
              <Panel title={t("applications.form.newTitle")}>
                <ApplicationForm
                  key={fromJob?.id ?? "blank"}
                  application={{
                    job_id: fromJob?.id ?? null,
                    company: fromJob?.company ?? "",
                    role: fromJob?.title ?? "",
                    stage: "draft",
                    applied_on: null,
                    next_step: "",
                    next_step_at: null,
                  }}
                  jobs={
                    jobs.data?.filter((job) => job.status !== "dismissed") ?? []
                  }
                  pending={add.isPending}
                  error={add.isError ? add.error.message : null}
                  onCancel={() => setEditing(null)}
                  onSubmit={(application) =>
                    add.mutate(application, {
                      onSuccess: () => setEditing(null),
                    })
                  }
                />
              </Panel>
            )}
            {edited && (
              <Panel
                title={t("applications.form.editTitle", {
                  name: edited.company,
                })}
              >
                <ApplicationForm
                  key={edited.id}
                  application={edited}
                  jobs={null}
                  pending={save.isPending}
                  error={save.isError ? save.error.message : null}
                  onCancel={() => setEditing(null)}
                  onSubmit={(application) =>
                    save.mutate(
                      { ...edited, ...application },
                      { onSuccess: () => setEditing(null) },
                    )
                  }
                  onDelete={() => {
                    if (
                      window.confirm(
                        t("applications.confirmDelete", {
                          name: edited.company,
                        }),
                      )
                    ) {
                      remove.mutate(edited.id);
                      setEditing(null);
                    }
                  }}
                />
              </Panel>
            )}
            {applications.data.length === 0 ? (
              <StateMessage>{t("applications.empty")}</StateMessage>
            ) : view === "board" ? (
              <ApplicationBoard
                applications={applications.data}
                onEdit={setEditing}
              />
            ) : (
              <ApplicationTable
                applications={applications.data}
                onEdit={setEditing}
              />
            )}
          </>
        )}
      </PageBody>
    </>
  );
}
