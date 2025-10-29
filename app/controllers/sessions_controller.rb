class SessionsController < ApplicationController
  include SessionAuthenticable

  def new
    redirect_to inventory_items_path if user_signed_in?
    @user = User.new
  end

  def create
    user = User.find_by(email: params[:email])

    if user&.authenticate(params[:password])
      sign_in(user)
      redirect_to inventory_items_path, notice: "Welcome back, #{user.first_name}!"
    else
      flash.now[:alert] = "Invalid email or password"
      @user = User.new(email: params[:email])
      render :new, status: :unprocessable_entity
    end
  end

  def destroy
    sign_out
    redirect_to root_path, notice: "Signed out successfully"
  end
end

