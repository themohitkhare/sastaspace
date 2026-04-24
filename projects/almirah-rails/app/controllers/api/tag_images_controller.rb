# frozen_string_literal: true

module Api
  # POST /almirah/api/tag_images
  #
  # Accepts a multipart/form-data upload with an `image` field (JPEG/PNG/WebP/GIF,
  # ≤ 8 MB). Runs the LiteLLM / Gemma 4 vision tagger and returns structured JSON.
  #
  # Auth-gated: returns 401 JSON when no session exists.
  # Error safety: upstream LiteLLM / Anthropic errors are logged server-side and
  # returned as a generic {"error": "tagging failed"} to the client.
  class TagImagesController < BaseController
    ALLOWED_TYPES = %w[image/jpeg image/png image/webp image/gif].freeze
    MAX_BYTES     = 8 * 1024 * 1024  # 8 MB

    def create
      file = params[:image]

      if file.nil?
        return render json: { error: "missing 'image' file" }, status: :bad_request
      end

      unless file.respond_to?(:content_type)
        return render json: { error: "expected multipart/form-data with an 'image' field" }, status: :unsupported_media_type
      end

      unless ALLOWED_TYPES.include?(file.content_type)
        return render json: { error: "unsupported media type: #{file.content_type.presence || 'unknown'}" }, status: :unsupported_media_type
      end

      if file.size > MAX_BYTES
        return render json: { error: "image too large (max 8 MB)" }, status: :payload_too_large
      end

      image_data = Base64.strict_encode64(file.read)
      media_type = file.content_type

      begin
        tagger = AlmirahTagger.new
        result = tagger.tag(image_data, media_type: media_type)
        render json: { ok: true, result: result }
      rescue AlmirahTagger::TaggerError => e
        Rails.logger.error "[tag_images] Tagger error: #{e.message}"
        render json: { error: "tagging failed" }, status: :bad_gateway
      rescue StandardError => e
        Rails.logger.error "[tag_images] Unexpected error: #{e.class} — #{e.message}"
        render json: { error: "tagging failed" }, status: :bad_gateway
      end
    end
  end
end
