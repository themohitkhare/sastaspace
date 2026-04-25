// Subscribe to the `project` table on the live SpacetimeDB module.
// Same dynamic-load pattern as ./spacetime.ts so the page renders cleanly
// before bindings exist (fresh clones).

import { STDB_MODULE, STDB_URI } from "./spacetime";

export type Project = {
  slug: string;
  title: string;
  blurb: string;
  status: string;
  tags: string[];
  url: string;
};

type ProjectsListener = (rows: readonly Project[]) => void;

const listeners = new Set<ProjectsListener>();
let lastRows: readonly Project[] = [];
let started = false;

function notify(rows: readonly Project[]) {
  lastRows = rows;
  for (const fn of listeners) fn(rows);
}

export function subscribeProjects(fn: ProjectsListener): () => void {
  listeners.add(fn);
  fn(lastRows);
  if (!started) {
    started = true;
    void start();
  }
  return () => {
    listeners.delete(fn);
  };
}

async function start(): Promise<void> {
  let bindings: Record<string, unknown>;
  try {
    bindings = (await import("@sastaspace/stdb-bindings")) as Record<string, unknown>;
  } catch {
    return;
  }

  const DbConnection = bindings.DbConnection as
    | { builder: () => StdbBuilder }
    | undefined;
  if (!DbConnection) return;

  let conn: StdbConn | null = null;
  conn = DbConnection.builder()
    .withUri(STDB_URI)
    .withDatabaseName(STDB_MODULE)
    .withLightMode(true)
    .onConnect(() => {
      if (!conn) return;
      conn
        .subscriptionBuilder()
        .onApplied(() => notify(snapshot(conn!)))
        .subscribe("SELECT * FROM project");
      conn.db.project.onInsert?.(() => notify(snapshot(conn!)));
      conn.db.project.onDelete?.(() => notify(snapshot(conn!)));
      conn.db.project.onUpdate?.(() => notify(snapshot(conn!)));
    })
    .onConnectError((_ctx: unknown, err: Error) => {
      console.warn("[sastaspace] stdb projects connect failed:", err?.message ?? err);
    })
    .build();
}

function snapshot(conn: StdbConn): readonly Project[] {
  const out: Project[] = [];
  for (const row of conn.db.project.iter() as Iterable<Project>) {
    out.push(row);
  }
  // Stable order: live first, then by title
  out.sort((a, b) => {
    if (a.status !== b.status) {
      if (a.status === "live") return -1;
      if (b.status === "live") return 1;
    }
    return a.title.localeCompare(b.title);
  });
  return out;
}

type StdbBuilder = {
  withUri: (uri: string) => StdbBuilder;
  withDatabaseName: (name: string) => StdbBuilder;
  withLightMode: (on: boolean) => StdbBuilder;
  onConnect: (fn: (ctx: unknown, identity: unknown, token: string) => void) => StdbBuilder;
  onConnectError: (fn: (ctx: unknown, err: Error) => void) => StdbBuilder;
  build: () => StdbConn;
};

type StdbConn = {
  db: {
    project: {
      iter: () => Iterable<unknown>;
      onInsert?: (fn: () => void) => void;
      onDelete?: (fn: () => void) => void;
      onUpdate?: (fn: () => void) => void;
    };
  };
  subscriptionBuilder: () => {
    onApplied: (fn: () => void) => any;
    subscribe: (q: string) => unknown;
  };
};
