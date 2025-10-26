class UpController < ApplicationController
  def show
    # Simple liveness check - just verify the app is running
    render json: {
      status: "up",
      timestamp: Time.current.iso8601
    }, status: :ok
  end
end
