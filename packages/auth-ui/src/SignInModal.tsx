"use client";
import { useState, useEffect, useRef, useCallback, type FormEvent } from "react";

/**
 * Traps keyboard focus within `containerRef` while the modal is open.
 * Queries all focusable elements on each Tab/Shift+Tab keystroke so that
 * dynamically-rendered children (e.g. the error paragraph) are always included.
 */
function useFocusTrap(containerRef: React.RefObject<HTMLElement | null>, active: boolean) {
  useEffect(() => {
    if (!active) return;
    const el = containerRef.current;
    if (!el) return;

    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      const focusable = Array.from(
        el!.querySelectorAll<HTMLElement>(
          'button, input, [href], select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((n) => !n.hasAttribute("disabled") && !n.closest("[aria-hidden]"));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    el.addEventListener("keydown", onKeyDown);
    return () => el.removeEventListener("keydown", onKeyDown);
  }, [containerRef, active]);
}

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
  const dialogRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);

  // Focus trap
  useFocusTrap(dialogRef, open);

  // Esc closes modal
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );
  useEffect(() => {
    if (!open) return;
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, handleKeyDown]);

  // Auto-focus first input on open
  useEffect(() => {
    if (open && firstInputRef.current) {
      firstInputRef.current.focus();
    }
  }, [open]);

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
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        ref={dialogRef}
        className="modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Sign in"
      >
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
              ref={firstInputRef}
              className="callsign-input"
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
