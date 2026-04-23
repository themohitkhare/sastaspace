"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function SignUpForm() {
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function signUp(formData: FormData) {
    setLoading(true);
    try {
      const supabase = createClient();
      const email = String(formData.get("email") || "");
      const password = String(formData.get("password") || "");
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
      });
      if (error) throw error;
      setSent(true);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <div className="rounded-md border bg-muted/30 p-4 text-sm">
        <p className="font-medium">Check your email</p>
        <p className="text-muted-foreground">
          We sent a confirmation link to the address you provided.
        </p>
      </div>
    );
  }

  return (
    <form action={signUp} className="grid gap-4">
      <div className="grid gap-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" name="email" type="email" required autoComplete="email" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          name="password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
        />
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "Creating account..." : "Create account"}
      </Button>
      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/sign-in" className="underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
