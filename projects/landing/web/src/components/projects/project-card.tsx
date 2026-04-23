import { StatusChip, type StatusValue } from "@/components/ui/status-chip";

export type Project = {
  id: number;
  slug: string;
  name: string;
  url: string;
  description: string;
  live_at: string | null;
  /** Optional — nullable until db/migrations add the column. Falls back to derived state. */
  status?: StatusValue | null;
  /** Optional tags. */
  tags?: string[] | null;
};

function deriveStatus(project: Project): StatusValue {
  if (project.status) return project.status;
  return project.live_at ? "live" : "wip";
}

export function ProjectCard({ project }: { project: Project }) {
  const status = deriveStatus(project);
  const hostname = project.url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  const tags = project.tags ?? [];

  return (
    <a
      href={project.url}
      target="_blank"
      rel="noreferrer"
      className="group block rounded-[var(--radius-lg)] border border-border bg-card p-6 transition-all hover:-translate-y-[1px] hover:border-foreground"
    >
      <div className="font-mono text-[11px] tracking-[0.04em] text-[var(--brand-sasta)]">
        {hostname}
      </div>
      <h3 className="mt-1.5 text-xl font-medium tracking-tight">{project.name}</h3>
      <p className="mt-1 text-[15px] leading-relaxed text-muted-foreground">
        {project.description}
      </p>
      <div className="mt-4 flex items-center justify-between gap-2">
        <StatusChip value={status} />
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-md bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </a>
  );
}
