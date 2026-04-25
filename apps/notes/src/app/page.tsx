import { listPosts } from "@/lib/posts";
import { TopBar } from "@/components/TopBar";
import { Footer } from "@/components/Footer";
import styles from "./notes.module.css";

export default async function NotesIndex() {
  const posts = await listPosts();

  return (
    <div className={styles.wrap}>
      <TopBar />

      <header className={styles.indexHeader}>
        <div className={styles.indexEyebrow}>workshop notes</div>
        <h1>Thinking out loud.</h1>
        <p className={styles.indexLede}>
          Short posts on what I'm making, why a thing is built a certain way, and the mistakes I'd
          rather you not repeat. Written for me six months from now.
        </p>
      </header>

      {posts.length === 0 ? (
        <div className={styles.empty}>
          <p>The workshop's quiet today. Come back soon.</p>
        </div>
      ) : (
        <ul className={styles.postList}>
          {posts.map((p) => (
            <li key={p.slug}>
              <span className={styles.postDate}>{formatDate(p.date)}</span>
              <div>
                <h2 className={styles.postTitle}>
                  <a href={`/${p.slug}`}>{p.title}</a>
                </h2>
                {p.summary && <p className={styles.postSummary}>{p.summary}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}

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
