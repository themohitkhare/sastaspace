import { NextRequest, NextResponse } from "next/server";

const TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

type ContactPayload = {
  name: string;
  email: string;
  message: string;
  honeypot?: string;
  turnstileToken?: string;
  source?: string;
};

const ESC_MAP = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
} as const;

const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ESC_MAP[c as keyof typeof ESC_MAP]);

async function verifyTurnstile(token: string, remoteip?: string): Promise<boolean> {
  const secret = process.env.TURNSTILE_SECRET_KEY;
  if (!secret) {
    return process.env.NODE_ENV !== "production";
  }

  if (!token) {
    return false;
  }

  const body = new URLSearchParams({
    secret,
    response: token,
  });

  if (remoteip) {
    body.set("remoteip", remoteip);
  }

  const res = await fetch(TURNSTILE_VERIFY_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
    cache: "no-store",
  });

  if (!res.ok) {
    return false;
  }

  const json = (await res.json()) as { success?: boolean };
  return Boolean(json.success);
}

export async function POST(req: NextRequest) {
  try {
    const origin = req.headers.get("origin") ?? "";
    const allowedOrigins = ["https://sastaspace.com"];
    const allowedSuffix = ".sastaspace.com";
    let originAllowed = process.env.NODE_ENV !== "production";
    if (!originAllowed && origin) {
      if (allowedOrigins.includes(origin)) {
        originAllowed = true;
      } else if (origin.startsWith("https://")) {
        try {
          originAllowed = new URL(origin).hostname.endsWith(allowedSuffix);
        } catch {
          originAllowed = false;
        }
      }
    }
    if (!originAllowed) {
      return NextResponse.json({ error: "Forbidden origin" }, { status: 403 });
    }

    const body = (await req.json()) as ContactPayload;

    if (body.honeypot) {
      return NextResponse.json({ ok: true });
    }

    if (!body.name || !body.email || !body.message) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    const token = body.turnstileToken ?? "";
    const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
    const verified = await verifyTurnstile(token, ip);
    if (!verified) {
      return NextResponse.json({ error: "Verification failed" }, { status: 400 });
    }

    const resendKey = process.env.RESEND_API_KEY;
    const ownerEmail = process.env.OWNER_EMAIL;
    if (!resendKey || !ownerEmail) {
      return NextResponse.json({ ok: true, skipped: true });
    }

    const payload = {
      from: "SastaSpace <onboarding@resend.dev>",
      to: [ownerEmail],
      subject: `New message from ${body.source || "project-bank"}`,
      html: `<p><strong>Name:</strong> ${esc(body.name)}</p><p><strong>Email:</strong> ${esc(body.email)}</p><p>${esc(body.message).replace(/\n/g, "<br>")}</p>`,
      text: `Name: ${body.name}\nEmail: ${body.email}\n\n${body.message}`,
    };

    const emailRes = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${resendKey}`,
      },
      body: JSON.stringify(payload),
    });

    if (!emailRes.ok) {
      return NextResponse.json({ error: "Email delivery failed" }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Contact route error", error);
    return NextResponse.json({ error: "Unexpected server error" }, { status: 500 });
  }
}
