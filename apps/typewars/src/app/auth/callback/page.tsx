"use client";
// PHASE 4 DELETE — legacy FastAPI fragment-based callback. Kept alive for
// one release per docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md
// § "/auth/callback page (which handles JWT-from-fragment after the FastAPI
// redirect) gets retired once /auth/verify is live". Cutover happens in
// Phase 3; this file is git rm'd in Phase 4 cleanup. Behavior is intentionally
// untouched in F2 so in-flight magic links from the FastAPI service keep
// working through cutover.
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const TOKEN_KEY = "typewars:auth_token";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"working" | "error">("working");
  const [message, setMessage] = useState("Completing sign-in…");

  useEffect(() => {
    // Token + email travel in the URL fragment so they never hit our server.
    function processCallback() {
      const hash = typeof window !== "undefined" ? window.location.hash : "";
      if (!hash || !hash.startsWith("#")) {
        setStatus("error");
        setMessage("Missing sign-in details. Please request a new magic link.");
        return;
      }
      const params = new URLSearchParams(hash.slice(1));
      const jwt = params.get("token");
      const email = params.get("email");
      if (!jwt || !email) {
        setStatus("error");
        setMessage("Sign-in details are incomplete. Please request a new magic link.");
        return;
      }
      try {
        window.localStorage.setItem(TOKEN_KEY, jwt);
      } catch {
        setStatus("error");
        setMessage("Could not store sign-in token (localStorage blocked?). Please try a different browser.");
        return;
      }
      // Strip the fragment so back-button doesn't re-trigger and so the JWT
      // doesn't sit in URL history.
      router.replace("/");
    }
    const timer = setTimeout(processCallback, 0);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="page" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <div style={{ textAlign: "center" }}>
        <p className="ss-eyebrow">~/typewars/auth/callback —</p>
        <p className="ss-body" style={{ marginTop: 8 }}>{message}</p>
        {status === "error" && (
          <button className="enlist-btn" onClick={() => router.replace("/")} style={{ marginTop: 16 }}>
            back to map →
          </button>
        )}
      </div>
    </div>
  );
}
