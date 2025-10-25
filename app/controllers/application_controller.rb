class ApplicationController < ActionController::Base
  include StructuredLogging
  include Instrumentation
  
  # Only allow modern browsers supporting webp images, web push, badges, import maps, CSS nesting, and CSS :has.
  allow_browser versions: :modern

  # Changes to the importmap will invalidate the etag for HTML responses
  stale_when_importmap_changes

  # Add request ID to all responses
  before_action :set_request_id_header

  private

  def set_request_id_header
    response.headers['X-Request-ID'] = request.env['REQUEST_ID']
  end
end
