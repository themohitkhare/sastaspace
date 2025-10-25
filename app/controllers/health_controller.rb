class HealthController < ApplicationController
  def show
    render json: { status: "healthy" }, status: :ok
  end
end
