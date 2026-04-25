import { notFound } from "next/navigation";
import { MDXRemote } from "next-mdx-remote/rsc";
import { listPosts, readPost } from "@/lib/posts";
import { TopBar } from "@/components/TopBar";
import { Footer } from "@/components/Footer";
import { Comments } from "@/components/Comments";
import styles from "../notes.module.css";

export const dynamicParams = false;

export async function generateStaticParams() {
  const posts = await listPosts({ includeDrafts: false });
  return posts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = await readPost(slug);
  if (!post) return {};
  return {
    title: `${post.meta.title} — notes — sastaspace`,
    description: post.meta.summary,
  };
}

export default async function PostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = await readPost(slug);
  if (!post) notFound();

  return (
    <div className={styles.wrap}>
      <TopBar />

      <article className={styles.article}>
        <div className={styles.articleMeta}>
          {formatDate(post.meta.date)}
          {post.meta.draft && " · DRAFT"}
        </div>
        <h1>{post.meta.title}</h1>
        <div className={styles.prose}>
          <MDXRemote source={post.body} />
        </div>
      </article>

      <Comments slug={slug} />
      <Footer />
    </div>
  );
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}
