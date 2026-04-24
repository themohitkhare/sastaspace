# frozen_string_literal: true

# AlmirahTagger — wraps AnthropicClient with the outfit-tagging prompt.
#
# Mirrors the TypeScript tagOutfitImage() in projects/almirah/web/src/lib/almirah/litellm.ts
# Returns a plain Ruby hash matching the ImageTagResult shape:
#
#   {
#     is_outfit_photo: true,
#     style_family: "ethnic-daily",
#     items_visible: [{ kind: "kurta", colour: "indigo", fabric_hint: "cotton", notes: nil }],
#     dominant_colours: ["indigo", "cream"],
#     occasion_hint: "casual-day",
#     people_count: 1
#   }
class AlmirahTagger
  class TaggerError < StandardError; end

  VISION_MODEL = ENV.fetch("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

  SYSTEM_PROMPT = <<~PROMPT.strip
    You are a South-Asian wardrobe cataloguer. You look at a user-supplied photo
    and return a short JSON description of the wearable items visible. Never invent
    items that aren't in the photo. Use Indian garment vocabulary where appropriate
    (kurta, saree, dupatta, lehenga, sherwani, kurti, salwar, churidar, dhoti, juttis)
    alongside western (shirt, jeans, blazer, t-shirt). Be terse — this is a catalogue,
    not a description.
  PROMPT

  TAG_PROMPT = <<~PROMPT.strip
    Look at this photo and return a single JSON object matching this shape —
    no prose, no markdown fence, just the raw JSON:

    {
      "is_outfit_photo": true,
      "style_family": "western-casual | western-formal | ethnic-festive | ethnic-daily | sports | sleepwear | unclear",
      "items_visible": [
        { "kind": "kurta", "colour": "indigo", "fabric_hint": "cotton", "notes": "block print" }
      ],
      "dominant_colours": ["indigo", "cream"],
      "occasion_hint": "office | wedding | diwali | casual-day | date | puja | travel | home | null",
      "people_count": 1
    }

    If is_outfit_photo is false, set items_visible to [] and style_family to "unclear".
  PROMPT

  def initialize(client: AnthropicClient.new)
    @client = client
  end

  # @param image_data [String] base64-encoded image bytes
  # @param media_type [String] "image/jpeg" | "image/png" | "image/webp" | "image/gif"
  # @return [Hash] structured tag result
  def tag(image_data, media_type: "image/jpeg")
    raw = @client.vision(
      TAG_PROMPT,
      image_data: image_data,
      media_type: media_type,
      model:      VISION_MODEL,
      max_tokens: 700
    )

    json_text = strip_fence(raw.strip)

    begin
      result = JSON.parse(json_text)
    rescue JSON::ParserError => e
      raise TaggerError, "model returned non-JSON output: #{raw.slice(0, 200)} — #{e.message}"
    end

    result
  end

  private

  def strip_fence(text)
    # Model may wrap JSON in ```json ... ``` — strip it.
    match = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/)
    match ? match[1].strip : text
  end
end
