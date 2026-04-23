import Link from "next/link";
import { ArrowUpRight, ExternalLink } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type Project = {
  id: number;
  slug: string;
  name: string;
  url: string;
  description: string;
  live_at: string | null;
};

export const dynamic = "force-dynamic";
export const revalidate = 0;

async function getProjects(): Promise<Project[]> {
  const base = process.env.POSTGREST_URL || "http://localhost:3001";
  try {
    const res = await fetch(
      `${base}/projects?live_at=not.is.null&order=live_at.desc`,
      { cache: "no-store" },
    );
    if (!res.ok) return [];
    return (await res.json()) as Project[];
  } catch {
    return [];
  }
}

export default async function LandingPage() {
  const projects = await getProjects();

  return (
    <AppShell projectName="SastaSpace">
      <section className="border-b">
        <div className="mx-auto max-w-5xl px-4 py-24 sm:py-32">
          <Badge variant="outline" className="mb-6 text-xs">
            Project Bank
          </Badge>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
            Small projects,
            <br />
            built and shipped.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
            SastaSpace is a home for small, self-hosted experiments. Each project lives on its own
            subdomain, shares one Postgres, and ships through a single pipeline.
          </p>
          <div className="mt-8 flex gap-3">
            <Button asChild size="lg">
              <Link href="#projects">See projects</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/contact">
                Get in touch
                <ArrowUpRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <section id="projects" className="mx-auto max-w-5xl px-4 py-16">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Live projects</h2>
            <p className="text-sm text-muted-foreground">
              Each one lives at a <code>*.sastaspace.com</code> subdomain.
            </p>
          </div>
          <p className="text-sm text-muted-foreground">
            {projects.length} {projects.length === 1 ? "project" : "projects"}
          </p>
        </div>

        {projects.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>No projects live yet</CardTitle>
              <CardDescription>
                Projects appear here when they&apos;re marked live in the database.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {projects.map((project) => (
              <a
                key={project.id}
                href={project.url}
                target="_blank"
                rel="noreferrer"
                className="group"
              >
                <Card className="h-full transition-colors group-hover:border-foreground/30">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <CardTitle className="group-hover:underline">{project.name}</CardTitle>
                      <ExternalLink className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <CardDescription>{project.url.replace(/^https?:\/\//, "")}</CardDescription>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {project.description}
                  </CardContent>
                </Card>
              </a>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
