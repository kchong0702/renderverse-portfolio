# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Today: one person, the owner, managing their own job search, career documents and portfolio site. Other job seekers are a planned later audience, so copy, empty states and onboarding must not assume the reader is the owner. Records already carry a `user_id`.

## Product Purpose

Ops is a career management workspace. It tracks job searching and applications (found, saved, applied, replied, interview, offer), keeps career documents (résumés, CVs, cover letters) and the facts they are built from, and manages the portfolio site's content and releases. Success is the user knowing where every application stands, what to do next, and having documents and a portfolio that stay current without duplicate effort.

## Positioning

The same profile, skills and projects that drive the career documents publish to the owner's Renderverse 3D portfolio site. Portfolio management lives inside the career workspace instead of being a separate tool.

## Operating Context

- Agents behind the UI: ezcareer-harness exposes two A2A agents, career-consultant (import a PDF résumé into an editable template, write or tailor résumés, CVs and cover letters) and job-finder (search jobs, analyse a posting, score fit against the profile). Ops is their client and owns all stored data and versions.
- artifact-service renders documents to HTML and PDF; ops shows those renders and lets the user edit text in place.
- A daily job-agent run is scheduled by ops; results arrive as scored candidates for the user to review.
- Portfolio work: profile, skills, projects, media assets, and releases that publish to the Renderverse site.

## Capabilities and Constraints

- Existing app: `apps/ops-web` (React 18, Vite, Tailwind 4, react-router, TanStack Query, zustand, i18next). Current routes: overview, profile, skills, projects, resume, imports, releases, plus an assistant chat panel.
- The sidebar should stay short; portfolio sections (profile, skills, projects, media, releases) group under one entry.
- Undecided: job sources beyond JSearch, table vs board as the default applications view, and whether interviews sync with an external calendar.

## Evidence on Hand

- Real content: the owner's profile, skills, projects and résumés in ops-api; three test résumé PDFs used as eval fixtures in the renderverse-portfolio repo.
- Absent: no application history, response rates or job data exist yet. Mockups must label any numbers as sample data and never present them as the owner's record.

## Product Principles

1. One source of truth: a fact entered once feeds résumés, letters and the portfolio.
2. Show where things stand and what to do next before anything else.
3. The user stays in control of outward actions; agents prepare, the user sends and publishes.
4. Career search comes first; portfolio management stays fully available but grouped.

## Accessibility & Inclusion

- Used for long stretches, often when tired: comfortable reading sizes, calm density, low glare.
- WCAG 2.2 AA contrast in every theme.
- A bright light theme is primary, and a dark theme is a binding requirement.
