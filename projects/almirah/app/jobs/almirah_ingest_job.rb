# frozen_string_literal: true

# AlmirahIngestJob — processes one photo from a bulk ingest batch.
#
# Runs via Solid Queue (the Rails 8 default job backend backed by Postgres).
#
# Flow:
#   1. Call LiteLLM vision tagger via AlmirahTagger.
#   2. Write a new project_almirah.items row for the current user.
#   3. Update the parent IngestJob status to "done" (or "error" on failure).
#
# Arguments:
#   ingest_job_id [String] UUID of the IngestJob record to update on completion.
#   user_id       [Integer]
#   image_data    [String] base64-encoded image bytes.
#   media_type    [String] "image/jpeg" etc.
class AlmirahIngestJob < ApplicationJob
  queue_as :default

  # Retry twice before marking the ingest job as errored.
  retry_on StandardError, attempts: 3, wait: :polynomially_longer

  discard_on ActiveRecord::RecordNotFound

  def perform(ingest_job_id, user_id, image_data, media_type)
    ingest_record = IngestJob.find(ingest_job_id)
    ingest_record.update!(status: "processing", started_at: Time.current)

    tagger = AlmirahTagger.new
    result = tagger.tag(image_data, media_type: media_type)

    # Only write an item row if the model says it's actually an outfit photo.
    if result["is_outfit_photo"]
      first_visible = result["items_visible"]&.first || {}
      kind = normalise_kind(first_visible["kind"].to_s)
      tone = normalise_tone(result["dominant_colours"]&.first.to_s)

      Item.create!(
        user_id:     user_id,
        kind:        kind,
        name:        build_name(result),
        tone:        tone,
        rack:        infer_rack(result["style_family"].to_s),
        wears_count: 0,
        photo_path:  nil  # Active Storage blob association wired separately
      )
    end

    ingest_record.update!(status: "done", finished_at: Time.current)
  rescue AlmirahTagger::TaggerError, StandardError => e
    Rails.logger.error "[AlmirahIngestJob] Error for job #{ingest_job_id}: #{e.message}"
    IngestJob.find_by(id: ingest_job_id)&.update!(
      status: "error",
      error_message: e.message.truncate(500),
      finished_at: Time.current
    )
    raise  # re-raise so Solid Queue can retry
  end

  private

  VALID_KINDS = Item::KINDS
  VALID_RACKS = Item::RACKS

  def normalise_kind(raw)
    VALID_KINDS.include?(raw) ? raw : "shirt"
  end

  def normalise_tone(colour_label)
    mapping = {
      "white" => "cream", "ivory" => "cream", "cream" => "cream", "off-white" => "cream",
      "blue"  => "indigo", "indigo" => "indigo", "navy" => "navy",
      "black" => "ink", "grey" => "ink", "gray" => "ink",
      "red"   => "red", "maroon" => "red", "crimson" => "red",
      "green" => "green", "olive" => "olive", "khaki" => "olive",
      "pink"  => "rose", "rose" => "rose",
      "yellow" => "warm", "orange" => "warm", "rust" => "warm",
      "sand"  => "sand", "beige" => "sand", "tan" => "sand",
      "denim" => "denim",
    }
    mapping.fetch(colour_label.downcase.strip, "warm")
  end

  def infer_rack(style_family)
    case style_family
    when "ethnic-festive", "ethnic-daily" then "ethnic"
    when "western-formal"                 then "office"
    else                                       "weekend"
    end
  end

  def build_name(result)
    first = result["items_visible"]&.first || {}
    parts = [
      first["colour"],
      first["fabric_hint"],
      first["kind"],
      first["notes"].presence&.then { |n| "(#{n})" },
    ].compact
    parts.empty? ? "imported item" : parts.join(" ")
  end
end
