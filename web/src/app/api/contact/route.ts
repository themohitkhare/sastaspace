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

    // 0. Env var guard — fail fast if not configured
    if (!process.env.RESEND_API_KEY || !process.env.OWNER_EMAIL) {
      return Response.json(
        { error: "Contact form is not configured. Please try again later." },
        { status: 503 }
      );
    }

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

    // 5. Send transactional email to submitter (only if subdomain provided)
    if (subdomain?.trim()) {
      const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "https://sastaspace.com";
      const redesignLink = `${baseUrl}/${subdomain}/`;
      try {
        await getResend().emails.send({
          from: `SastaSpace <noreply@sastaspace.com>`,
          to: [email],
          subject: "Your SastaSpace Redesign is Ready",
          html: `
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 24px;">
              <h1 style="font-size: 24px; font-weight: 600; color: #1a1a1a; margin: 0 0 16px;">
                Thanks for your interest, ${escapeHtml(name)}!
              </h1>
              <p style="font-size: 16px; line-height: 1.6; color: #444; margin: 0 0 24px;">
                Your AI-powered website redesign is ready to view.
              </p>
              <a href="${redesignLink}" style="display: inline-block; background-color: #b8860b; color: #1a1a1a; text-decoration: none; font-weight: 500; font-size: 16px; padding: 12px 28px; border-radius: 8px;">
                View Your Redesign
              </a>
              <p style="font-size: 14px; line-height: 1.6; color: #666; margin: 24px 0 0;">
                Or copy this link: <a href="${redesignLink}" style="color: #b8860b;">${redesignLink}</a>
              </p>
              <hr style="border: none; border-top: 1px solid #e5e5e5; margin: 32px 0;" />
              <p style="font-size: 14px; line-height: 1.6; color: #666; margin: 0;">
                Want to make it real? Reply to this email or
                <a href="mailto:${process.env.OWNER_EMAIL}" style="color: #b8860b;">book a consultation</a>.
              </p>
              <p style="font-size: 12px; color: #999; margin: 24px 0 0;">
                SastaSpace &mdash; AI Website Redesigner
              </p>
              <p style="color: #999; font-size: 12px; margin-top: 32px; border-top: 1px solid #eee; padding-top: 16px;">
                You received this because you submitted a redesign request on SastaSpace.
                <br />This is a one-time email &mdash; we won't send more unless you reach out.
              </p>
            </div>
          `,
        });
      } catch (emailErr) {
        // Transactional email failure is non-blocking
        console.error("Transactional email error:", emailErr);
      }
    }

    return Response.json({ ok: true });
  } catch {
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
