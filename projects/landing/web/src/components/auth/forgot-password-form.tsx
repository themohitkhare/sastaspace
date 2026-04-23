"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ForgotPasswordForm() {
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function requestReset(formData: FormData) {
    setLoading(true);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.resetPasswordForEmail(
        String(formData.get("email") || ""),
        { redirectTo: `${window.location.origin}/auth/callback?next=/account` },
      );
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
        <p className="font-medium">Reset link sent</p>
        <p className="text-muted-foreground">
          Check your inbox for a password reset link.
        </p>
      </div>
    );
  }

  return (
    <form action={requestReset} className="grid gap-4">
      <div className="grid gap-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" name="email" type="email" required autoComplete="email" />
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "Sending..." : "Send reset link"}
      </Button>
      <p className="text-center text-sm text-muted-foreground">
        Back to{" "}
        <Link href="/sign-in" className="underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
