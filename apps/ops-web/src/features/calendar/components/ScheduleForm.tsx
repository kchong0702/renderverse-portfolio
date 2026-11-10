import { useState } from "react";
import { useTranslation } from "react-i18next";
import { GoogleNotice } from "@/features/settings";
import { ApiError } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import { TextField } from "@/shared/components/fields";
import Panel from "@/shared/components/Panel";
import { useCreateEvent } from "../hooks/useEvents";

export default function ScheduleForm({
  day,
  onDone,
}: {
  day: string;
  onDone: (day: string | null) => void;
}) {
  const { t } = useTranslation();
  const create = useCreateEvent();
  const [event, setEvent] = useState({
    title: "",
    day,
    from: "10:00",
    to: "11:00",
    location: "",
  });

  return (
    <Panel title={t("calendar.schedule.title")}>
      <form
        className="flex flex-col gap-4"
        onSubmit={(submit) => {
          submit.preventDefault();
          create.mutate(
            {
              title: event.title,
              start: new Date(`${event.day}T${event.from}`).toISOString(),
              end: new Date(`${event.day}T${event.to}`).toISOString(),
              ...(event.location && { location: event.location }),
            },
            { onSuccess: () => onDone(event.day) },
          );
        }}
      >
        <TextField
          label={t("calendar.schedule.name")}
          required
          value={event.title}
          onChange={(change) =>
            setEvent({ ...event, title: change.target.value })
          }
        />
        <div className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-3.5">
          <TextField
            label={t("calendar.schedule.day")}
            type="date"
            required
            value={event.day}
            onChange={(change) =>
              setEvent({ ...event, day: change.target.value })
            }
          />
          <TextField
            label={t("calendar.schedule.from")}
            type="time"
            required
            value={event.from}
            onChange={(change) =>
              setEvent({ ...event, from: change.target.value })
            }
          />
          <TextField
            label={t("calendar.schedule.to")}
            type="time"
            required
            value={event.to}
            onChange={(change) =>
              setEvent({ ...event, to: change.target.value })
            }
          />
        </div>
        <TextField
          label={t("calendar.schedule.location")}
          value={event.location}
          onChange={(change) =>
            setEvent({ ...event, location: change.target.value })
          }
        />
        {create.isError &&
          (create.error instanceof ApiError && create.error.status === 409 ? (
            <GoogleNotice
              problem="reconnect"
              reason={create.error.message}
              next="/calendar"
            />
          ) : (
            <p role="alert" className="text-crit m-0 text-[14px]">
              {t("calendar.schedule.failed", { reason: create.error.message })}
            </p>
          ))}
        <div className="flex flex-wrap gap-2.5">
          <button
            type="submit"
            className={buttonClass("primary")}
            disabled={create.isPending}
          >
            {t("calendar.schedule.add")}
          </button>
          <button
            type="button"
            className={buttonClass()}
            onClick={() => onDone(null)}
          >
            {t("calendar.schedule.cancel")}
          </button>
        </div>
      </form>
    </Panel>
  );
}
