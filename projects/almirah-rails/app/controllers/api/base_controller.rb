# frozen_string_literal: true

module Api
  class BaseController < ApplicationController
    # API controllers skip HTML browser checking.
    skip_before_action :allow_browser

    # Return JSON 401 instead of redirecting to sign-in for unauthenticated API calls.
    rescue_from StandardError do |e|
      Rails.logger.error "[API] Unhandled error: #{e.class} — #{e.message}"
      render json: { error: "internal server error" }, status: :internal_server_error
    end

    private

    def require_authentication
      return if Current.session

      render json: { error: "unauthenticated" }, status: :unauthorized
    end
  end
end
