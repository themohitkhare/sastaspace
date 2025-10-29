class RegistrationsController < ApplicationController
  include SessionAuthenticable

  def new
    redirect_to inventory_items_path if user_signed_in?
    @user = User.new
  end

  def create
    # Call JWT API to register user
    response = Auth::SessionService.register(user_params.to_h, request)

    if response[:success]
      # Store tokens in httpOnly cookies
      cookies.signed[:access_token] = {
        value: response[:data][:token],
        httponly: true,
        secure: Rails.env.production?,
        same_site: :lax,
        expires: 15.minutes.from_now
      }
      cookies.signed[:refresh_token] = {
        value: response[:data][:refresh_token],
        httponly: true,
        secure: Rails.env.production?,
        same_site: :lax,
        expires: 7.days.from_now
      }

      # Set current user for immediate use
      @current_user = User.find(response[:data][:user][:id])
      session[:user_id] = @current_user.id

      redirect_to inventory_items_path, notice: "Welcome, #{@current_user.first_name}! Your account has been created."
    else
      @user = User.new(user_params)
      @errors = response[:error][:details] || {}
      flash.now[:alert] = response[:error][:message] || "Registration failed"
      render :new, status: :unprocessable_entity
    end
  end

  private

  def user_params
    params.require(:user).permit(:email, :first_name, :last_name, :password, :password_confirmation)
  end
end
