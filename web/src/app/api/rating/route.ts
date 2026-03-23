import { NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { subdomain, rating, comment } = body;

    if (!subdomain || typeof rating !== "number" || rating < 1 || rating > 5) {
      return Response.json({ error: "Invalid rating" }, { status: 400 });
    }

    console.log(
      `[rating] subdomain=${subdomain} rating=${rating}${comment ? ` comment="${comment}"` : ""}`
    );

    return Response.json({ ok: true });
  } catch {
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
