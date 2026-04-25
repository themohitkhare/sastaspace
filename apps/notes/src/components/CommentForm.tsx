"use client";

import { useEffect, useState } from "react";
import { getSession, subscribe, type Session } from "@/lib/auth";
import { submitComment } from "@/lib/comments";
import styles from "./comments.module.css";

type State =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "queued" }
  | { kind: "error"; message: string };

export function CommentForm({ slug }: { slug: string }) {
  const [session, setSession] = useState<Session | null>(null);
  const [name, setName] = useState("");
  const [body, setBody] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  useEffect(() => subscribe((s) => setSession(s)), []);
  useEffect(() => {
    if (typeof window !== "undefined") setSession(getSession());
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = body.trim();
    if (trimmed.length < 4) {
      setState({ kind: "error", message: "Comment too short (min 4 characters)." });
      return;
    }
    if (trimmed.length > 4000) {
      setState({ kind: "error", message: "Comment too long (max 4000 characters)." });
      return;
    }
    setState({ kind: "submitting" });
    try {
      // For signed-in users, name is ignored — author_name is sourced from
      // the User row server-side, so signed-in users can't impersonate.
      await submitComment(slug, name.trim(), trimmed);
      setBody("");
      setState({ kind: "queued" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to send.";
      setState({ kind: "error", message });
    }
  }

  if (state.kind === "queued") {
    return (
      <div className={styles.queued}>
        <p>
          Sent. The moderator's looking it over — if it's fine it'll show up here in a few seconds.
        </p>
        <button
          type="button"
          className={styles.queuedReset}
          onClick={() => setState({ kind: "idle" })}
        >
          write another →
        </button>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      {session ? (
        <div className={styles.signedInNote}>
          posting as <strong>{session.display_name}</strong>
        </div>
      ) : (
        <div className={styles.formRow}>
          <label className={styles.label} htmlFor="cf-name">
            name <span className={styles.optional}>(optional · sign in for a persistent name)</span>
          </label>
          <input
            id="cf-name"
            className={styles.input}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={64}
            placeholder="visitor"
            autoComplete="off"
          />
        </div>
      )}
      <div className={styles.formRow}>
        <label className={styles.label} htmlFor="cf-body">
          comment
        </label>
        <textarea
          id="cf-body"
          className={styles.textarea}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={4000}
          rows={5}
          placeholder="What's on your mind?"
          required
        />
      </div>
      <div className={styles.formActions}>
        {state.kind === "error" && <span className={styles.error}>{state.message}</span>}
        <button
          className={styles.submit}
          type="submit"
          disabled={state.kind === "submitting"}
        >
          {state.kind === "submitting" ? "sending…" : "post comment →"}
        </button>
      </div>
    </form>
  );
}
