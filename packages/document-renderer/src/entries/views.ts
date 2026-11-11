import type {
  Award,
  Certification,
  CustomEntry,
  Date,
  Degree,
  Job,
  Project,
  Publication,
} from "../generated/document";
import type { EntryFields, EntryKind, EntryView } from "../types";

const date = (value?: Date | null) => value?.text.text;

export const entryFields: Record<EntryKind, EntryFields> = {
  experience: {
    title: "role",
    subtitle: "company",
    dates: "dates",
    place: "location",
  },
  education: {
    title: "degree",
    subtitle: "school",
    dates: "dates",
    place: "location",
  },
  projects: { title: "name", subtitle: "role", dates: "dates" },
  certifications: { title: "name", subtitle: "issuer", dates: "date" },
  awards: { title: "title", subtitle: "awarder", dates: "date" },
  publications: { title: "title", subtitle: "venue", dates: "date" },
  custom: {
    title: "title",
    subtitle: "subtitle",
    dates: "dates",
    place: "location",
  },
};

export const entryViews: {
  experience: (job: Job) => EntryView;
  education: (degree: Degree) => EntryView;
  projects: (project: Project) => EntryView;
  certifications: (certification: Certification) => EntryView;
  awards: (award: Award) => EntryView;
  publications: (publication: Publication) => EntryView;
  custom: (entry: CustomEntry) => EntryView;
} = {
  experience: (job) => ({
    ...job,
    title: job.role.text,
    subtitle: job.company.text,
    dates: date(job.dates),
    place: job.location?.text,
    text: job.description,
  }),
  education: (degree) => ({
    ...degree,
    title: degree.degree.text,
    subtitle: degree.school.text,
    dates: date(degree.dates),
    place: degree.location?.text,
    note: degree.grade?.text,
  }),
  projects: (project) => ({
    ...project,
    title: project.name.text,
    subtitle: project.role?.text,
    dates: date(project.dates),
    text: project.description,
    tags: project.tags?.map((tag) => tag.text.text),
  }),
  certifications: (certification) => ({
    ...certification,
    title: certification.name.text,
    subtitle: certification.issuer?.text,
    dates: date(certification.date),
  }),
  awards: (award) => ({
    ...award,
    title: award.title.text,
    subtitle: award.awarder?.text,
    dates: date(award.date),
  }),
  publications: (publication) => ({
    ...publication,
    title: publication.title.text,
    subtitle: publication.venue?.text,
    dates: date(publication.date),
    note: [
      publication.authors?.map((author) => author.text).join(", "),
      publication.doi && `doi:${publication.doi.text}`,
    ]
      .filter(Boolean)
      .join(" · "),
  }),
  custom: (entry) => ({
    ...entry,
    title: entry.title.text,
    subtitle: entry.subtitle?.text,
    dates: date(entry.dates),
    place: entry.location?.text,
  }),
};
