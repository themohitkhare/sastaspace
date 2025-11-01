class SessionsController < ApplicationController
  include SessionAuthenticable

  def new
    redirect_to inventory_items_path if user_signed_in?
    @user = User.new
  end

  def create
    # Check if remember_me checkbox was checked
    remember_me = params[:remember_me].present? && (params[:remember_me] == "1" || params[:remember_me] == true)

    # Call JWT API to login user, passing remember_me
    response = Auth::SessionService.login(params[:email], params[:password], request, remember_me: remember_me)

    if response[:success]
      # Set cookie expiration to match refresh token expiration in database
      refresh_token_expires = remember_me ? 30.days.from_now : 7.days.from_now

      Rails.logger.debug "Remember me: #{remember_me}, refresh token expires in: #{refresh_token_expires}"

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
        expires: refresh_token_expires
      }

      # Set current user for immediate use
      @current_user = User.find(response[:data][:user][:id])
      session[:user_id] = @current_user.id

      redirect_to inventory_items_path, notice: "Welcome back, #{@current_user.first_name}!"
    else
      flash.now[:alert] = response[:error][:message] || "Invalid email or password"
      @user = User.new(email: params[:email])
      render :new, status: :unprocessable_entity
    end
  end

  def destroy
    # Call logout API to invalidate token
    logout_user_via_api if cookies.signed[:access_token]

    # Clear cookies and session
    cookies.delete(:access_token)
    cookies.delete(:refresh_token)
    sign_out

    redirect_to root_path, notice: "Signed out successfully"
  end

  private


  def logout_user_via_api
    token = cookies.signed[:access_token]
    return unless token

    uri = URI("#{request.base_url}/api/v1/auth/logout")
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = uri.scheme == "https"

    request_obj = Net::HTTP::Post.new(uri.path, {
      "Content-Type" => "application/json",
      "Authorization" => "Bearer #{token}"
    })

    http.request(request_obj)
  rescue StandardError
    # Silently fail on logout - cookies are cleared anyway
  end
end
