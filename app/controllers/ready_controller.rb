class ReadyController < ApplicationController
  def show
    render json: { status: "ready" }, status: :ok
  end
end
