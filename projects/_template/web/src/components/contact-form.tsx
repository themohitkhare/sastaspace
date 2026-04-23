"use client";

import { useState } from "react";

export function ContactForm() {
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string>("");

  async function onSubmit(formData: FormData) {
    setStatus("submitting");
    setError("");

    const payload = {
      name: String(formData.get("name") || ""),
      email: String(formData.get("email") || ""),
      message: String(formData.get("message") || ""),
      honeypot: String(formData.get("company") || ""),
      turnstileToken: String(formData.get("cf-turnstile-response") || ""),
      source: "__NAME__",
    };

    const res = await fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      setStatus("success");
      return;
    }

    const body = (await res.json().catch(() => ({}))) as { error?: string };
    setStatus("error");
    setError(body.error ?? "Failed to send message");
  }

  return (
    <form
      action={async (fd) => {
        await onSubmit(fd);
      }}
      style={{ display: "grid", gap: 12, maxWidth: 480 }}
    >
      <input name="name" placeholder="Name" required />
      <input name="email" type="email" placeholder="Email" required />
      <textarea name="message" placeholder="Message" required rows={5} />
      <input name="company" style={{ display: "none" }} tabIndex={-1} autoComplete="off" />
      <button type="submit" disabled={status === "submitting"}>
        {status === "submitting" ? "Sending..." : "Send"}
      </button>
      {status === "success" ? <p>Message sent.</p> : null}
      {status === "error" ? <p>{error}</p> : null}
    </form>
  );
}
