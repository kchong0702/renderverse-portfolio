import type { ContactKind } from "./schema/document";

export type SectionKind =
  | "summary"
  | "experience"
  | "education"
  | "projects"
  | "skills"
  | "languages"
  | "certifications"
  | "awards"
  | "publications"
  | "custom";

interface Text {
  headings: Record<SectionKind, string>;
  contacts: Record<ContactKind, string>;
}

const texts: Record<string, Text> = {
  en: {
    headings: {
      summary: "Summary",
      experience: "Experience",
      education: "Education",
      projects: "Projects",
      skills: "Skills",
      languages: "Languages",
      certifications: "Certifications",
      awards: "Awards",
      publications: "Publications",
      custom: "More",
    },
    contacts: {
      email: "Email",
      phone: "Phone",
      location: "Location",
      linkedin: "LinkedIn",
      github: "GitHub",
      website: "Website",
      other: "Link",
    },
  },
  ms: {
    headings: {
      summary: "Ringkasan",
      experience: "Pengalaman",
      education: "Pendidikan",
      projects: "Projek",
      skills: "Kemahiran",
      languages: "Bahasa",
      certifications: "Pensijilan",
      awards: "Anugerah",
      publications: "Penerbitan",
      custom: "Lain-lain",
    },
    contacts: {
      email: "E-mel",
      phone: "Telefon",
      location: "Lokasi",
      linkedin: "LinkedIn",
      github: "GitHub",
      website: "Laman web",
      other: "Pautan",
    },
  },
};

/** Default headings and labels in the document's language, or English */
export const textFor = (language = "en"): Text =>
  texts[language.split("-")[0]] ?? texts.en;
