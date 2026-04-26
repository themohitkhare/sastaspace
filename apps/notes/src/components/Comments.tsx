"use client";

import { useEffect, useState } from "react";
import { subscribeComments, type Comment } from "@/lib/comments";
import { CommentForm } from "./CommentForm";
import styles from "./comments.module.css";

const VISIBLE_COUNT = 5;

export function Comments({ slug }: { slug: string }) {
  const [comments, setComments] = useState<readonly Comment[] | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => subscribeComments(slug, (c) => setComments(c)), [slug]);

  const hiddenCount = comments && comments.length > VISIBLE_COUNT && !expanded
    ? comments.length - VISIBLE_COUNT
    : 0;
  const visible = comments && hiddenCount > 0
    ? comments.slice(-VISIBLE_COUNT)
    : comments;

  return (
    <section className={styles.section} aria-label="Comments">
      <div className={styles.header}>
        <div className={styles.eyebrow}>comments</div>
        <h2>What people said.</h2>
      </div>

      {comments === null ? (
        // Connecting state — distinguished from empty so users don't read
        // "No comments yet" before the WebSocket subscription has applied.
        // UX audit M1.
        <div className={styles.empty} aria-busy="true" aria-live="polite">
          <p>Loading comments…</p>
        </div>
      ) : comments.length === 0 ? (
        <div className={styles.empty}>
          <p>No comments yet. Be the first to break the silence.</p>
        </div>
      ) : (
        <ul className={styles.list}>
          {hiddenCount > 0 && (
            <li className={styles.showOlderItem}>
              <button
                className={styles.showOlder}
                onClick={() => setExpanded(true)}
              >
                ↑ {hiddenCount} older comment{hiddenCount !== 1 ? "s" : ""}
              </button>
            </li>
          )}
          {visible!.map((c) => (
            <li key={String(c.id)}>
              <div className={styles.commentMeta}>
                <span className={styles.commentName}>{c.authorName}</span>
                <span className={styles.commentDot}> · </span>
                <span className={styles.commentDate}>{formatDate(c.createdAt)}</span>
              </div>
              <p className={styles.commentBody}>{c.body}</p>
            </li>
          ))}
        </ul>
      )}

      <CommentForm slug={slug} />
    </section>
  );
}

function formatDate(ms: number): string {
  if (!ms) return "—";
  const d = new Date(ms);
  return d.toISOString().slice(0, 10);
}
