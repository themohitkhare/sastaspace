"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ContactForm({ source = "SastaSpace" }: { source?: string }) {
  const [status, setStatus] = useState<"idle" | "submitting" | "success">("idle");

  async function onSubmit(formData: FormData) {
    setStatus("submitting");

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
    toast.error(body.error ?? "Failed to send message");
    setStatus("idle");
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
          className="flex min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </div>
      <input
        name="company"
        className="hidden"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
      />
      <Button type="submit" disabled={status === "submitting"}>
        {status === "submitting" ? "Sending..." : status === "success" ? "Sent" : "Send message"}
      </Button>
    </form>
  );
}
