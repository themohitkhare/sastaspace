// Build-time content reader. Pulls .mdx files from ../../content/posts,
// parses frontmatter, returns sorted-by-date PostMeta[] and the raw body
// (server side only — `fs` import). Drafts are filtered out in the public
// listing but still readable by direct slug.

import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";

export type PostMeta = {
  slug: string;
  title: string;
  date: string;
  summary?: string;
  draft?: boolean;
};

export type Post = {
  meta: PostMeta;
  body: string;
};

const POSTS_DIR = path.join(process.cwd(), "content", "posts");

export async function listPosts(opts: { includeDrafts?: boolean } = {}): Promise<PostMeta[]> {
  let entries: string[];
  try {
    entries = await fs.readdir(POSTS_DIR);
  } catch {
    return [];
  }
  const all = await Promise.all(
    entries
      .filter((e) => e.endsWith(".mdx"))
      .map(async (file) => {
        const slug = file.replace(/\.mdx$/, "");
        const raw = await fs.readFile(path.join(POSTS_DIR, file), "utf8");
        const { data } = matter(raw);
        return {
          slug,
          title: typeof data.title === "string" ? data.title : slug,
          date: typeof data.date === "string" ? data.date : "",
          summary: typeof data.summary === "string" ? data.summary : undefined,
          draft: data.draft === true,
        } satisfies PostMeta;
      }),
  );
  const visible = opts.includeDrafts ? all : all.filter((p) => !p.draft);
  return visible.sort((a, b) => (a.date < b.date ? 1 : -1));
}

export async function readPost(slug: string): Promise<Post | null> {
  const file = path.join(POSTS_DIR, `${slug}.mdx`);
  let raw: string;
  try {
    raw = await fs.readFile(file, "utf8");
  } catch {
    return null;
  }
  const { data, content } = matter(raw);
  return {
    meta: {
      slug,
      title: typeof data.title === "string" ? data.title : slug,
      date: typeof data.date === "string" ? data.date : "",
      summary: typeof data.summary === "string" ? data.summary : undefined,
      draft: data.draft === true,
    },
    body: content,
  };
}
