"use client";

import { useEffect, useState } from "react";
import { subscribeComments, type Comment } from "@/lib/comments";
import { CommentForm } from "./CommentForm";
import styles from "./comments.module.css";

export function Comments({ slug }: { slug: string }) {
  const [comments, setComments] = useState<readonly Comment[] | null>(null);

  useEffect(() => subscribeComments(slug, (c) => setComments(c)), [slug]);

  return (
    <section className={styles.section} aria-label="Comments">
      <div className={styles.header}>
        <div className={styles.eyebrow}>comments</div>
        <h2>What people said.</h2>
      </div>

      {comments === null || comments.length === 0 ? (
        <div className={styles.empty}>
          <p>No comments yet. Be the first to break the silence.</p>
        </div>
      ) : (
        <ul className={styles.list}>
          {comments.map((c) => (
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
