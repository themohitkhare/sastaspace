# frozen_string_literal: true

class AdminController < ApplicationController
  before_action :require_admin

  def index
    # Admin dashboard — coming soon.
  end

  private

  def require_admin
    redirect_to root_path, alert: "Not authorised." unless Current.user&.admin?
  end
end
