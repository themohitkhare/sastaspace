// web/src/lib/env.ts
//
// Runtime environment for client components.
// In production (k8s), values come from window.__ENV__ injected by entrypoint.sh.
// In local dev, falls back to process.env (set by Next.js from .env files).

function getEnv(key: string): string | undefined {
  if (typeof window !== "undefined" && window.__ENV__) {
    return window.__ENV__[key];
  }
  // Fallback for SSR and local dev — Next.js inlines NEXT_PUBLIC_* at build time
  return process.env[key];
}

export function getBackendUrl(): string {
  return getEnv("NEXT_PUBLIC_BACKEND_URL") ?? "http://localhost:8080";
}

export function getTurnstileSiteKey(): string {
  return getEnv("NEXT_PUBLIC_TURNSTILE_SITE_KEY") ?? "";
}

export function isTurnstileEnabled(): boolean {
  return getEnv("NEXT_PUBLIC_ENABLE_TURNSTILE") !== "false";
}

// TypeScript augmentation for window.__ENV__
declare global {
  interface Window {
    __ENV__?: Record<string, string>;
  }
}
