"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { getSafeNext } from "@/lib/safe-next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

type LoadingKind = "password" | "google" | "github" | null;

export function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState<LoadingKind>(null);

  // `next` can be a same-origin path ("/dashboard") or an absolute URL on a
  // *.sastaspace.com subdomain (e.g. "https://almirah.sastaspace.com/today").
  // getSafeNext collapses anything else to "/" to prevent open-redirects.
  const rawNext = searchParams.get("next");
  const nextTarget =
    typeof window !== "undefined" ? getSafeNext(rawNext, window.location.origin) : "/";

  function redirectToOptions() {
    // Always route the OAuth callback through landing's /auth/callback — it's
    // the one place that exchanges the code and sets the shared-domain cookie.
    // After exchange, the callback redirects onwards to `next` (which can be a
    // same-origin path or a cross-subdomain absolute URL, re-validated there).
    const origin =
      typeof window !== "undefined" ? window.location.origin : "https://sastaspace.com";
    return {
      redirectTo: `${origin}/auth/callback?next=${encodeURIComponent(nextTarget)}`,
    };
  }

  async function signInWithPassword(formData: FormData) {
    setLoading("password");
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithPassword({
        email: String(formData.get("email") || ""),
        password: String(formData.get("password") || ""),
      });
      if (error) throw error;
      if (nextTarget.startsWith("http")) {
        window.location.href = nextTarget;
      } else {
        router.push(nextTarget);
        router.refresh();
      }
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  async function signInWithProvider(provider: "google" | "github") {
    setLoading(provider);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: redirectToOptions(),
      });
      if (error) throw error;
    } catch (err) {
      toast.error((err as Error).message);
      setLoading(null);
    }
  }

  return (
    <div className="grid gap-6">
      <div className="grid gap-2">
        <Button
          variant="default"
          onClick={() => signInWithProvider("google")}
          disabled={loading === "google"}
        >
          {loading === "google" ? "Redirecting..." : "Continue with Google"}
        </Button>
        <Button
          variant="outline"
          onClick={() => signInWithProvider("github")}
          disabled={loading === "github"}
        >
          {loading === "github" ? "Redirecting..." : "Continue with GitHub"}
        </Button>
      </div>

      <Separator />

      <form action={signInWithPassword} className="grid gap-4">
        <div className="grid gap-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" name="email" type="email" required autoComplete="email" />
        </div>
        <div className="grid gap-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link
              href="/forgot-password"
              className="text-xs text-muted-foreground underline-offset-4 hover:underline"
            >
              Forgot?
            </Link>
          </div>
          <Input
            id="password"
            name="password"
            type="password"
            required
            autoComplete="current-password"
          />
        </div>
        <Button type="submit" variant="outline" disabled={loading === "password"}>
          {loading === "password" ? "Signing in..." : "Sign in with password"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        New here?{" "}
        <Link href="/sign-up" className="underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
