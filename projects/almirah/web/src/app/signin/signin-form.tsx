"use client";

import { useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

type Status =
  | { kind: "idle" }
  | { kind: "sending-link" }
  | { kind: "link-sent"; email: string }
  | { kind: "sending-oauth" }
  | { kind: "error"; message: string };

export function SignInForm() {
  const search = useSearchParams();
  const next = search.get("next") || "/";
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function handleMagicLink(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email) return;
    setStatus({ kind: "sending-link" });
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
        },
      });
      if (error) throw error;
      setStatus({ kind: "link-sent", email });
    } catch (err) {
      const message = err instanceof Error ? err.message : "couldn't send magic link";
      setStatus({ kind: "error", message });
    }
  }

  async function handleGoogle() {
    setStatus({ kind: "sending-oauth" });
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
        },
      });
      if (error) throw error;
      // Supabase redirects the browser — no further local state to set.
    } catch (err) {
      const message = err instanceof Error ? err.message : "couldn't start Google sign-in";
      setStatus({ kind: "error", message });
    }
  }

  if (status.kind === "link-sent") {
    return (
      <div style={{ marginTop: 30, padding: 16, border: "1px solid var(--brand-ink)", borderRadius: 10 }}>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          check your email
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.5 }}>
          We sent a sign-in link to <strong>{status.email}</strong>. Open it on this device to continue.
        </div>
      </div>
    );
  }

  const sending = status.kind === "sending-link" || status.kind === "sending-oauth";

  return (
    <div style={{ marginTop: 30, display: "flex", flexDirection: "column", gap: 10 }}>
      <button
        type="button"
        className="btn btn--primary btn--block"
        onClick={handleGoogle}
        disabled={sending}
      >
        <span>{status.kind === "sending-oauth" ? "redirecting…" : "continue with Google"}</span>
      </button>
      <form onSubmit={handleMagicLink} style={{ display: "contents" }}>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="field"
          placeholder="or email me a magic link"
          disabled={sending}
        />
        <button type="submit" className="btn btn--ghost btn--block" disabled={sending || !email}>
          {status.kind === "sending-link" ? "sending…" : "send link →"}
        </button>
      </form>
      {status.kind === "error" && (
        <div
          style={{
            fontSize: 12,
            color: "var(--brand-sasta-text)",
            fontFamily: "var(--font-mono)",
            marginTop: 4,
          }}
        >
          {status.message}
        </div>
      )}
    </div>
  );
}
