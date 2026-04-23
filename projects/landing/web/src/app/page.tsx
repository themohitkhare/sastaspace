import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { ProjectCard, type Project } from "@/components/projects/project-card";

export const revalidate = 300;

async function getProjects(): Promise<Project[]> {
  const base = process.env.POSTGREST_URL || "http://localhost:3001";
  try {
    const res = await fetch(`${base}/projects?order=live_at.desc.nullslast`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return [];
    return (await res.json()) as Project[];
  } catch {
    return [];
  }
}

export default async function LandingPage() {
  const projects = await getProjects();

  return (
    <AppShell>
      <Hero />
      <LabSection />
      <ProjectsSection projects={projects} />
      <NotesSection />
      <AboutSection />
    </AppShell>
  );
}

/* --------- sections --------- */

function Hero() {
  return (
    <section className="mx-auto max-w-5xl px-6 pb-14 pt-16 sm:px-8 sm:pt-20">
      <div className="font-mono text-xs tracking-[0.05em] text-muted-foreground">
        ~/mohit · sastaspace.com
      </div>
      <h1 className="mt-5 max-w-4xl text-[44px] leading-[1.02] tracking-[-0.025em] sm:text-[68px]">
        A <span className="text-[var(--brand-sasta)]">sasta</span> lab for the
        things I want to build.
      </h1>
      <p className="mt-6 max-w-2xl text-[17px] leading-relaxed text-foreground/85 sm:text-[19px] sm:leading-[1.55]">
        This is my workshop on the open internet. I make the small things I want
        to exist — tools, toys, half-built experiments — and put them somewhere
        anyone can use them. Cheap to build. Cheap to run. Open to share.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="#projects"
          className="rounded-[10px] bg-[var(--brand-ink)] px-5 py-3 text-[15px] font-medium text-[var(--brand-paper)] transition-colors hover:bg-[var(--brand-rust)] dark:bg-[var(--brand-paper)] dark:text-[var(--brand-ink)] dark:hover:bg-[var(--brand-dust)]"
        >
          see the lab →
        </Link>
        <Link
          href="#about"
          className="rounded-[10px] border border-border px-5 py-3 text-[15px] font-medium text-foreground transition-colors hover:border-foreground"
        >
          about the idea
        </Link>
      </div>
    </section>
  );
}

function LabSection() {
  const principles = [
    {
      num: "01 / sasta",
      title: "Cheap to build.",
      body: "Boring tools. Shared infrastructure. New projects cost closer to zero than they do to a weekend brunch. The bill stays small so the imagination stays loud.",
    },
    {
      num: "02 / shipped",
      title: "One command to live.",
      body: "Every experiment gets its own subdomain and goes from an idea to a working URL in the time it takes to name it. If it doesn't ship, it doesn't count.",
    },
    {
      num: "03 / shared",
      title: "Open by default.",
      body: "Open URL, open source, open to being copied, forked, or improved on. The lab is on the internet so other people can find it — including me, six months from now.",
    },
  ];

  return (
    <section
      id="lab"
      className="mx-auto max-w-5xl border-t border-border px-6 py-20 sm:px-8"
    >
      <div className="font-mono text-xs tracking-[0.08em] text-[var(--brand-sasta-text)]">
        the idea
      </div>
      <h2 className="mt-3.5 text-[32px] leading-[1.1] tracking-[-0.02em] sm:text-[42px]">
        Not a portfolio. A lab.
      </h2>
      <p className="mt-6 max-w-2xl text-[17px] leading-[1.6] text-foreground/85 sm:text-[18px]">
        Portfolios edit for wins. Labs show the whole bench. Sastaspace runs on
        three rules — the ones that make it possible to keep shipping small
        things without turning each one into a startup.
      </p>

      <div className="mt-10 grid gap-5 sm:grid-cols-3">
        {principles.map((p) => (
          <div
            key={p.num}
            className="rounded-[var(--radius-lg)] border border-border bg-card p-6"
          >
            <div className="font-mono text-xs tracking-[0.08em] text-[var(--brand-sasta-text)]">
              {p.num}
            </div>
            <h3 className="mt-2.5 text-xl font-medium tracking-tight">
              {p.title}
            </h3>
            <p className="mt-1.5 text-[15px] leading-[1.6] text-foreground/80">
              {p.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ProjectsSection({ projects }: { projects: Project[] }) {
  return (
    <section
      id="projects"
      className="mx-auto max-w-5xl border-t border-border px-6 py-20 sm:px-8"
    >
      <div className="flex items-end justify-between">
        <div>
          <div className="font-mono text-xs tracking-[0.08em] text-[var(--brand-sasta-text)]">
            projects
          </div>
          <h2 className="mt-3.5 text-[32px] leading-[1.1] tracking-[-0.02em] sm:text-[42px]">
            What&apos;s on the bench.
          </h2>
        </div>
        {projects.length > 0 && (
          <div className="font-mono text-xs text-muted-foreground">
            {projects.length} on display · more in the drawer
          </div>
        )}
      </div>

      {projects.length === 0 ? (
        <div className="mt-10 rounded-[var(--radius-lg)] border border-dashed border-border bg-card px-6 py-14 text-center">
          <p className="text-[17px] text-foreground">
            The workshop&apos;s quiet today. Come back soon.
          </p>
        </div>
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </section>
  );
}

function NotesSection() {
  const notes = [
    "Why everything here shares one database.",
    "A subdomain is the cheapest deployable unit I know.",
    "How to keep a side project from becoming a second job.",
  ];

  return (
    <section
      id="notes"
      className="mx-auto max-w-5xl border-t border-border px-6 py-20 sm:px-8"
    >
      <div className="font-mono text-xs tracking-[0.08em] text-[var(--brand-sasta-text)]">
        workshop notes
      </div>
      <h2 className="mt-3.5 text-[32px] leading-[1.1] tracking-[-0.02em] sm:text-[42px]">
        Thinking out loud.
      </h2>
      <p className="mt-6 max-w-2xl text-[17px] leading-[1.6] text-foreground/85">
        Short posts on what I&apos;m making, why a thing is built a certain way,
        and the mistakes I&apos;d rather you not repeat. Written for me six
        months from now.
      </p>
      <ul className="mt-8 divide-y divide-border border-y border-border">
        {notes.map((title) => (
          <li
            key={title}
            className="flex flex-col gap-2 py-3.5 sm:flex-row sm:items-baseline sm:gap-5"
          >
            <span className="min-w-[96px] font-mono text-xs tracking-[0.04em] text-muted-foreground">
              · coming soon
            </span>
            <span className="text-[17px] font-medium text-foreground">
              {title}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AboutSection() {
  return (
    <section
      id="about"
      className="mx-auto max-w-5xl border-t border-border px-6 py-20 sm:px-8"
    >
      <div className="grid gap-10 sm:grid-cols-[1fr_1.25fr] sm:gap-16">
        <div>
          <div className="font-mono text-xs tracking-[0.08em] text-[var(--brand-sasta-text)]">
            about
          </div>
          <h2 className="mt-3.5 text-[32px] leading-[1.1] tracking-[-0.02em] sm:text-[42px]">
            Hi — I&apos;m Mohit.
          </h2>
        </div>
        <div className="space-y-4 text-[17px] leading-[1.7] text-foreground/90">
          <p>
            I&apos;m a software engineer in Bengaluru. I spend my days on the
            unglamorous end of software — making slow things fast, fragile
            things dependable, complicated things small. I like boring tools
            that age well.
          </p>
          <p>
            Sastaspace is the other half. It&apos;s where I build what I want to
            build — without asking anyone for a roadmap — and put it on the
            internet for whoever might want it. Some things here will get
            polished. Some will stay half-built forever. All of them are out in
            the open.
          </p>
          <p>
            If any of this is interesting, the best way to follow along is to
            bookmark{" "}
            <Link
              href="#notes"
              className="text-[var(--brand-sasta-text)] underline-offset-4 hover:underline"
            >
              the notes
            </Link>
            , or grab the{" "}
            <Link
              href="/rss.xml"
              className="text-[var(--brand-sasta-text)] underline-offset-4 hover:underline"
            >
              RSS feed
            </Link>
            .
          </p>

          <div className="mt-6 rounded-[var(--radius-lg)] border border-border bg-card p-6">
            <div className="font-mono text-[11px] tracking-[0.06em] text-muted-foreground">
              the lab, in one line
            </div>
            <dl className="mt-3 divide-y divide-border">
              {[
                ["Run by", "one person"],
                ["Budget", "sasta — close to ₹0"],
                ["Roadmap", "none on purpose"],
                ["Default state", "open to the public"],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-2 text-[15px]">
                  <dt className="font-medium text-foreground">{label}</dt>
                  <dd className="text-foreground/80">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </section>
  );
}
