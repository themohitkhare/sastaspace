import { NextRequest } from "next/server";
import { Resend } from "resend";

function getResend() {
  return new Resend(process.env.RESEND_API_KEY);
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, email, message, website, turnstileToken, subdomain } = body;

    // 1. Honeypot — return success to not reveal detection (per D-10)
    if (website) {
      return Response.json({ ok: true });
    }

    // 2. Basic server-side validation
    if (!name?.trim() || !email?.trim() || !message?.trim()) {
      return Response.json({ error: "All fields are required" }, { status: 400 });
    }

    // 3. Turnstile verification (per D-09; conditional per FLAG-02)
    const turnstileEnabled =
      process.env.NEXT_PUBLIC_ENABLE_TURNSTILE !== "false";
    if (turnstileEnabled) {
      const turnstileRes = await fetch(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            secret: process.env.TURNSTILE_SECRET_KEY,
            response: turnstileToken,
          }),
        }
      );
      const turnstileData = await turnstileRes.json();
      if (!turnstileData.success) {
        return Response.json(
          { error: "Verification failed" },
          { status: 400 }
        );
      }
    }

    // 4. Send email via Resend (per D-15, D-16, D-17)
    const domain = subdomain?.replace(/-/g, ".") || "unknown";
    const { error } = await getResend().emails.send({
      from: `SastaSpace <noreply@sastaspace.com>`,
      to: [process.env.OWNER_EMAIL!],
      replyTo: email,
      subject: `New inquiry from ${escapeHtml(name)} — SastaSpace`,
      html: `
        <h2>New inquiry from SastaSpace</h2>
        <p><strong>Name:</strong> ${escapeHtml(name)}</p>
        <p><strong>Email:</strong> ${escapeHtml(email)}</p>
        <p><strong>Was viewing:</strong> ${escapeHtml(domain)}</p>
        <hr />
        <p>${escapeHtml(message).replace(/\n/g, "<br />")}</p>
      `,
    });

    if (error) {
      console.error("Resend error:", error);
      return Response.json({ error: "Failed to send message" }, { status: 500 });
    }

    return Response.json({ ok: true });
  } catch {
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
