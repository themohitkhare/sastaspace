import Link from "next/link";

type Project = {
  id: number;
  slug: string;
  name: string;
  url: string;
  description: string;
  live_at: string | null;
};

async function getProjects(): Promise<Project[]> {
  const base = process.env.POSTGREST_URL || "http://localhost:3001";
  try {
    const res = await fetch(
      `${base}/projects?live_at=not.is.null&order=live_at.desc`,
      { next: { revalidate: 60 } }
    );

    if (!res.ok) {
      return [];
    }

    return (await res.json()) as Project[];
  } catch {
    return [];
  }
}

export default async function LandingPage() {
  const projects = await getProjects();

  return (
    <main style={{ padding: 24, fontFamily: "system-ui", maxWidth: 920, margin: "0 auto" }}>
      <h1>SastaSpace Project Bank</h1>
      <p>Small projects deployed on sastaspace.com subdomains.</p>
      <p>
        <Link href="/contact">Contact</Link>
      </p>

      <section>
        <h2>Live Projects</h2>
        {projects.length === 0 ? (
          <p>No projects are marked live yet.</p>
        ) : (
          <ul>
            {projects.map((project) => (
              <li key={project.id} style={{ marginBottom: 10 }}>
                <a href={project.url} target="_blank" rel="noreferrer">
                  {project.name}
                </a>
                <div>{project.description}</div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
