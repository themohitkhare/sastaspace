# Session-based authentication for HTML controllers
module SessionAuthenticable
  extend ActiveSupport::Concern

  included do
    helper_method :current_user, :user_signed_in?
  end

  private

  def authenticate_user!
    unless session[:user_id]
      redirect_to login_path, alert: "Please sign in to continue"
      return
    end

    @current_user ||= User.find_by(id: session[:user_id])
    unless @current_user
      session.delete(:user_id)
      redirect_to login_path, alert: "Please sign in to continue"
    end
  end

  def current_user
    @current_user ||= User.find_by(id: session[:user_id]) if session[:user_id]
  end

  def user_signed_in?
    current_user.present?
  end

  def sign_in(user)
    session[:user_id] = user.id
    @current_user = user
  end

  def sign_out
    session.delete(:user_id)
    @current_user = nil
  end
end

