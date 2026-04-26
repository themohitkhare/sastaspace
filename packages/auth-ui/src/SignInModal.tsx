"use client";
import { useState, type FormEvent } from "react";

export interface SignInModalProps {
  /** App identifier sent to the auth service so the right callback is used. */
  app: "notes" | "typewars";
  /** Public URL the auth service should redirect to after verification.
   *  Auth service ignores this if it has its own per-app callback env var,
   *  but we send it for transparency. */
  callback: string;
  /** Optional previous SpacetimeDB identity hex (no 0x prefix needed) — used
   *  by typewars to claim guest progress at sign-in. Pass undefined for
   *  notes or when the caller has no prior identity to claim. */
  prevIdentity?: string;
  /** Auth service base URL. Defaults to production. */
  authBase?: string;
  open: boolean;
  onClose: () => void;
  /**
   * Phase 2 F1: optional override. When provided, the modal calls this with
   * the trimmed email instead of POSTing to {authBase}/auth/request. Used by
   * the STDB-native path so the modal stays presentational and the reducer
   * call lives in the consuming app. Throw to surface an error in the modal.
   */
  onRequest?: (email: string) => Promise<void>;
}

export function SignInModal({ app, callback, prevIdentity, authBase, open, onClose, onRequest }: SignInModalProps) {
  const base = authBase ?? "https://auth.sastaspace.com";
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setError(null);
    try {
      if (onRequest) {
        // STDB-native path — caller owns the network call (typically a
        // request_magic_link reducer dispatch). The modal stays purely
        // presentational and only handles UI state.
        await onRequest(email);
      } else {
        // Legacy FastAPI default — kept identical to pre-F1 behavior so
        // call-sites that don't opt into STDB get byte-identical wire
        // semantics.
        const body: Record<string, unknown> = { email, app, callback };
        if (prevIdentity) body.prev_identity = prevIdentity;
        const r = await fetch(`${base}/auth/request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const detail = await r.text().catch(() => "");
          throw new Error(detail || `HTTP ${r.status}`);
        }
      }
      setStatus("sent");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "request failed");
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2 className="ss-h3">Sign in</h2>
          <button className="link-btn" type="button" onClick={onClose}>close</button>
        </div>
        {status === "sent" ? (
          <p className="ss-body" style={{ marginTop: 12 }}>
            Check your inbox — magic link sent to <strong>{email}</strong>.
            {prevIdentity && " Open the link in this same browser to keep your progress."}
          </p>
        ) : (
          <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}>
            <p className="ss-small" style={{ color: "var(--brand-muted)" }}>
              We&apos;ll email you a one-time link. No password.
            </p>
            <input
              className="callsign-input"
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
            />
            <button className="enlist-btn" type="submit" disabled={status === "sending" || !email.trim()}>
              {status === "sending" ? "sending…" : "send magic link →"}
            </button>
            {error && (
              <p className="ss-small" style={{ color: "var(--brand-sasta-text)" }}>{error}</p>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
