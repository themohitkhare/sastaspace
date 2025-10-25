class UpController < ApplicationController
  def show
    render json: { status: "up" }, status: :ok
  end
end
