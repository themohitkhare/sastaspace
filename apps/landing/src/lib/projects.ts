// Static project list. Lives in the source so the landing page builds with
// `output: 'export'` (no runtime STDB call needed). Update this array +
// redeploy when a project goes live, changes status, or is added.
//
// The earlier dynamic-via-STDB design (subscribeProjects + upsert_project
// reducer) was over-engineered for a 3-project list that changes once a
// month at most. The `project` table + reducers in modules/sastaspace stay
// for now — Phase 4 cleanup will drop them.

export type ProjectStatus = "live" | "wip" | "paused" | "open source" | "archived" | "beta";

export type Project = {
  slug: string;
  title: string;
  blurb: string;
  status: ProjectStatus;
  tags: string[];
  url: string;
};

export const PROJECTS: readonly Project[] = [
  {
    slug: "notes",
    title: "Workshop notes",
    blurb:
      "Short posts on what I'm making, why a thing is built a certain way, and the mistakes I'd rather you not repeat.",
    status: "live",
    tags: ["writing", "public"],
    url: "https://notes.sastaspace.com",
  },
  {
    slug: "typewars",
    title: "TypeWars",
    blurb:
      "A cooperative typing game where five Legions liberate regions one word at a time. Multiplayer over a SpacetimeDB module.",
    status: "live",
    tags: ["game", "multiplayer", "stdb"],
    url: "https://typewars.sastaspace.com",
  },
  {
    slug: "deck",
    title: "Deck",
    blurb:
      "Brief → plan → audio assembly. NLP picks tracks before MusicGen renders them so you know what you're listening to before you hear it.",
    status: "beta",
    tags: ["audio", "lab", "ai"],
    url: "https://sastaspace.com/lab/deck",
  },
];
