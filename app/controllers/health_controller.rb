class HealthController < ApplicationController
  def show
    health_status = HealthChecker.check_all

    render json: health_status, status: health_status[:status] == "healthy" ? :ok : :service_unavailable
  end
end
