import Anthropic from "@anthropic-ai/sdk";

// LiteLLM speaks Anthropic protocol (anthropic_proxy enabled). We point the
// official SDK at it and use Claude-shaped model names; LiteLLM rewrites to
// ollama_chat/gemma4:31b under the hood. This keeps the code portable — switch
// to real Anthropic later by swapping env vars alone.

let _client: Anthropic | null = null;

function baseUrl(): string {
  return (
    process.env.LITELLM_BASE_URL ||
    process.env.ANTHROPIC_BASE_URL ||
    ""
  );
}

export function getClient(): Anthropic {
  if (_client) return _client;
  const apiKey = process.env.LITELLM_API_KEY || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error(
      "Missing LITELLM_API_KEY (or ANTHROPIC_API_KEY) — set it in .env.local or the k8s secret",
    );
  }
  const url = baseUrl();
  _client = new Anthropic({
    apiKey,
    ...(url ? { baseURL: url } : {}),
  });
  return _client;
}

// Model name used for vision / tagging. We target the Claude-shaped alias
// rather than gemma4-31b so a drop-in swap back to real Anthropic needs no
// code changes.
export const VISION_MODEL = "claude-haiku-4-5-20251001";

// Shape we ask the model to return for an uploaded garment/outfit photo.
export interface ImageTagResult {
  is_outfit_photo: boolean;
  style_family:
    | "western-casual"
    | "western-formal"
    | "ethnic-festive"
    | "ethnic-daily"
    | "sports"
    | "sleepwear"
    | "unclear";
  items_visible: Array<{
    kind: string;   // kurta | saree | shirt | jeans | dupatta | ...
    colour: string; // short label — "indigo", "off-white", "rust"
    fabric_hint?: string | null;
    notes?: string | null;
  }>;
  dominant_colours: string[];
  occasion_hint: string | null;
  people_count: number;
}

const SYSTEM_PROMPT = `You are a South-Asian wardrobe cataloguer. You look at a user-supplied photo and return a short JSON description of the wearable items visible. Never invent items that aren't in the photo. Use Indian garment vocabulary where appropriate (kurta, saree, dupatta, lehenga, sherwani, kurti, salwar, churidar, dhoti, juttis) alongside western (shirt, jeans, blazer, t-shirt). Be terse — this is a catalogue, not a description.`;

const TAG_PROMPT = `Look at this photo and return a single JSON object matching this TypeScript type — no prose, no markdown fence, just the raw JSON:

\`\`\`ts
{
  is_outfit_photo: boolean,              // true if a person is visibly wearing clothes; false for empty rooms, food, landscapes, screenshots
  style_family: "western-casual" | "western-formal" | "ethnic-festive" | "ethnic-daily" | "sports" | "sleepwear" | "unclear",
  items_visible: Array<{
    kind: string,        // lowercase, one word where possible — e.g. "kurta", "saree", "dupatta", "shirt", "jeans", "blazer", "juttis"
    colour: string,      // short label — "indigo", "off-white", "rust"
    fabric_hint?: string, // optional — "cotton", "silk", "linen", "denim" — only if visually obvious
    notes?: string        // optional — "block print", "embroidered", "chikankari", "stonewashed"
  }>,
  dominant_colours: string[], // 1–3 labels
  occasion_hint: string | null, // "office", "wedding", "diwali", "casual-day", "date", "puja", "travel", "home" — or null
  people_count: number
}
\`\`\`

If is_outfit_photo is false, set items_visible to [] and style_family to "unclear".`;

export async function tagOutfitImage(
  imageBase64: string,
  mediaType: "image/jpeg" | "image/png" | "image/webp" | "image/gif",
): Promise<ImageTagResult> {
  const client = getClient();

  const response = await client.messages.create({
    model: VISION_MODEL,
    max_tokens: 700,
    temperature: 0.1,
    system: SYSTEM_PROMPT,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "image",
            source: {
              type: "base64",
              media_type: mediaType,
              data: imageBase64,
            },
          },
          { type: "text", text: TAG_PROMPT },
        ],
      },
    ],
  });

  const text = response.content
    .filter((block): block is Anthropic.TextBlock => block.type === "text")
    .map((block) => block.text)
    .join("")
    .trim();

  // Model might wrap JSON in ```json ... ``` — strip it.
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
  const jsonText = (fenced ? fenced[1] : text).trim();

  let parsed: ImageTagResult;
  try {
    parsed = JSON.parse(jsonText) as ImageTagResult;
  } catch (err) {
    throw new Error(
      `model returned non-JSON output: ${text.slice(0, 200)}${err instanceof Error ? " — " + err.message : ""}`,
    );
  }
  return parsed;
}
