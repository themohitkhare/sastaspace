"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

export function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next") ?? "/";
  const [loading, setLoading] = useState<"password" | "magic" | "google" | "github" | null>(null);

  async function signInWithPassword(formData: FormData) {
    setLoading("password");
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithPassword({
        email: String(formData.get("email") || ""),
        password: String(formData.get("password") || ""),
      });
      if (error) throw error;
      router.push(nextPath);
      router.refresh();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  async function signInWithMagicLink(formData: FormData) {
    setLoading("magic");
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOtp({
        email: String(formData.get("email") || ""),
        options: { emailRedirectTo: `${window.location.origin}/auth/callback?next=${nextPath}` },
      });
      if (error) throw error;
      toast.success("Check your email for a login link");
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
        options: { redirectTo: `${window.location.origin}/auth/callback?next=${nextPath}` },
      });
      if (error) throw error;
    } catch (err) {
      toast.error((err as Error).message);
      setLoading(null);
    }
  }

  return (
    <div className="grid gap-6">
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
        <Button type="submit" disabled={loading === "password"}>
          {loading === "password" ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <Separator />

      <form action={signInWithMagicLink} className="grid gap-2">
        <Label htmlFor="magic-email" className="text-xs text-muted-foreground">
          Or email me a magic link
        </Label>
        <div className="flex gap-2">
          <Input id="magic-email" name="email" type="email" required placeholder="you@example.com" />
          <Button type="submit" variant="outline" disabled={loading === "magic"}>
            {loading === "magic" ? "Sending" : "Send link"}
          </Button>
        </div>
      </form>

      <div className="grid gap-2">
        <Button
          variant="outline"
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

      <p className="text-center text-sm text-muted-foreground">
        New here?{" "}
        <Link href="/sign-up" className="underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
