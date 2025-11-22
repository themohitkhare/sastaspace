# frozen_string_literal: true

# Public pages controller for landing page and marketing content
class PagesController < ApplicationController
  # Landing page
  # Redirects to inventory if user is already logged in
  def home
    if user_signed_in?
      redirect_to inventory_items_path
    else
      render :home
    end
  end
end
