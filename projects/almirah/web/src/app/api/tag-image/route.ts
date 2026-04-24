import { NextResponse, type NextRequest } from "next/server";
import { getSessionUser } from "@/lib/supabase/auth-helpers";
import { tagOutfitImage } from "@/lib/almirah/litellm";

export const runtime = "nodejs";
export const maxDuration = 60;

const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const MAX_BYTES = 8 * 1024 * 1024; // 8 MB

export async function POST(request: NextRequest) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  const contentType = request.headers.get("content-type") || "";
  if (!contentType.startsWith("multipart/form-data")) {
    return NextResponse.json(
      { error: "expected multipart/form-data with an 'image' field" },
      { status: 415 },
    );
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json({ error: "invalid form data" }, { status: 400 });
  }

  const file = form.get("image");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "missing 'image' file" }, { status: 400 });
  }
  if (!ALLOWED_TYPES.has(file.type)) {
    return NextResponse.json(
      { error: `unsupported media type: ${file.type || "unknown"}` },
      { status: 415 },
    );
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json({ error: "image too large (max 8 MB)" }, { status: 413 });
  }

  const bytes = Buffer.from(await file.arrayBuffer());
  const base64 = bytes.toString("base64");

  try {
    const result = await tagOutfitImage(
      base64,
      file.type as "image/jpeg" | "image/png" | "image/webp" | "image/gif",
    );
    return NextResponse.json({ ok: true, result });
  } catch (err) {
    // Log full context server-side; never leak upstream SDK / LiteLLM error
    // messages to the client — those include the internal cluster DNS
    // (litellm.litellm.svc.cluster.local:4000) and raw model output.
    console.error("[tag-image]", err);
    return NextResponse.json({ error: "tagging failed" }, { status: 502 });
  }
}
