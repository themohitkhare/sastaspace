"use client";

import { useState } from "react";
import { Turnstile } from "@marsidev/react-turnstile";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ContactForm({ source = "__NAME__" }: { source?: string }) {
  const [status, setStatus] = useState<"idle" | "submitting" | "success">("idle");
  const [error, setError] = useState<string | null>(null);
  const turnstileSiteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

  async function onSubmit(formData: FormData) {
    setStatus("submitting");
    setError(null);

    const payload = {
      name: String(formData.get("name") || ""),
      email: String(formData.get("email") || ""),
      message: String(formData.get("message") || ""),
      honeypot: String(formData.get("company") || ""),
      turnstileToken: String(formData.get("cf-turnstile-response") || ""),
      source,
    };

    const res = await fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      toast.success("Message sent");
      setStatus("success");
      return;
    }

    const body = (await res.json().catch(() => ({}))) as { error?: string };
    const msg = body.error ?? "Couldn't send the message. Try again, or email me directly.";
    setError(msg);
    toast.error(msg);
    setStatus("idle");
  }

  if (status === "success") {
    return (
      <div
        role="status"
        className="max-w-md rounded-[var(--radius-lg)] border border-border bg-card p-6"
      >
        <p className="font-medium">Sent.</p>
        <p className="mt-3 text-sm text-muted-foreground">
          I read everything. Reply comes from my own email.
        </p>
      </div>
    );
  }

  return (
    <form action={onSubmit} className="grid max-w-md gap-4">
      <div className="grid gap-2">
        <Label htmlFor="name">Name</Label>
        <Input id="name" name="name" required autoComplete="name" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" name="email" type="email" required autoComplete="email" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="message">Message</Label>
        <textarea
          id="message"
          name="message"
          required
          rows={5}
          className="flex min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
      <input
        name="company"
        className="hidden"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
      />
      {turnstileSiteKey && (
        <Turnstile siteKey={turnstileSiteKey} options={{ theme: "auto" }} />
      )}
      {error && (
        <p id="form-error" role="alert" className="text-sm text-[var(--brand-rust)]">
          {error}
        </p>
      )}
      <Button
        type="submit"
        disabled={status === "submitting"}
        aria-describedby={error ? "form-error" : undefined}
      >
        {status === "submitting" ? "Sending..." : "Send message"}
      </Button>
    </form>
  );
}
