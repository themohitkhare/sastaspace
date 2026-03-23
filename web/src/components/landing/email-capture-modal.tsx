"use client";

import { useEffect, useState, useCallback } from "react";
import { X } from "lucide-react";

const STORAGE_KEY = "sastaspace_email_dismissed";

export function EmailCaptureModal() {
  const [visible, setVisible] = useState(false);
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const dismiss = useCallback(() => {
    setVisible(false);
    try {
      sessionStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // Storage unavailable — silently ignore
    }
  }, []);

  useEffect(() => {
    // Only on desktop, only once per session
    if (typeof window === "undefined") return;
    if (window.innerWidth < 768) return;
    try {
      if (sessionStorage.getItem(STORAGE_KEY)) return;
    } catch {
      return;
    }

    const handler = (e: MouseEvent) => {
      if (e.clientY <= 5) {
        setVisible(true);
        document.removeEventListener("mouseout", handler);
      }
    };

    // Small delay so it doesn't fire immediately on page load
    const timer = setTimeout(() => {
      document.addEventListener("mouseout", handler);
    }, 5000);

    return () => {
      clearTimeout(timer);
      document.removeEventListener("mouseout", handler);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    try {
      await fetch("/api/analytics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: "email_captured", email: email.trim() }),
      });
    } catch {
      // Fire-and-forget — don't block the UI
    }

    setSubmitted(true);
    setTimeout(dismiss, 2000);
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="relative w-full max-w-md mx-4 rounded-xl border border-border bg-background p-8 shadow-2xl">
        <button
          onClick={dismiss}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>

        {submitted ? (
          <div className="text-center py-4">
            <p className="text-lg font-heading text-foreground">Thanks!</p>
            <p className="text-sm text-muted-foreground mt-1">
              We&apos;ll let you know when your redesign is ready.
            </p>
          </div>
        ) : (
          <>
            <h2 className="font-heading text-xl text-foreground">
              Wait! Get your free redesign
            </h2>
            <p className="text-sm text-muted-foreground mt-2 mb-6">
              Drop your email and we&apos;ll send you a link when your site redesign is ready.
            </p>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="flex-1 rounded-lg border border-border bg-background px-4 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-accent/50"
              />
              <button
                type="submit"
                className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background hover:bg-foreground/90 transition-colors"
              >
                Notify me
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
