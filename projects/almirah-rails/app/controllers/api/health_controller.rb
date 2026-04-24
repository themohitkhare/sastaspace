# frozen_string_literal: true

module Api
  class HealthController < BaseController
    allow_unauthenticated_access

    def show
      render json: {
        status:  "ok",
        app:     "almirah",
        version: Rails.application.config.version || "dev",
        db:      db_ok?,
      }
    end

    private

    def db_ok?
      ActiveRecord::Base.connection.execute("SELECT 1").any?
      true
    rescue StandardError
      false
    end
  end
end
