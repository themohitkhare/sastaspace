# frozen_string_literal: true

module Api
  class BaseController < ApplicationController
    # API controllers skip HTML browser checking. `allow_browser` in
    # ApplicationController registers an anonymous before_action under the
    # hood (Rails 8 internal), so referencing it by symbol fails in
    # production eager-load with "has not been defined". raise: false makes
    # the skip a no-op if the callback isn't present under this name.
    skip_before_action :allow_browser, raise: false

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
