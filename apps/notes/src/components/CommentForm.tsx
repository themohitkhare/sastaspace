"use client";

import { useEffect, useState } from "react";
import { subscribe, type Session } from "@/lib/auth";
import { submitComment } from "@/lib/comments";
import styles from "./comments.module.css";

function openSignInModal() {
  // AuthMenu listens for this event and pops its modal.
  window.dispatchEvent(new CustomEvent("sastaspace:open-signin"));
}

type State =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "queued" }
  | { kind: "error"; message: string };

export function CommentForm({ slug }: { slug: string }) {
  const [session, setSession] = useState<Session | null>(null);
  const [body, setBody] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  // subscribe() also fires the callback immediately with the current
  // session, so we don't need a separate getSession() effect.
  useEffect(() => subscribe((s) => setSession(s)), []);

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
      await submitComment(slug, trimmed);
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

  if (!session) {
    return (
      <div className={styles.gate}>
        <p>
          Sign in to leave a comment. We use a one-click email link — no
          password — so the moderator queue stays clean and you keep your
          name across visits.
        </p>
        <button
          type="button"
          className={styles.submit}
          onClick={openSignInModal}
        >
          sign in to comment →
        </button>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <div className={styles.signedInNote}>
        posting as <strong>{session.display_name}</strong>
      </div>
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
