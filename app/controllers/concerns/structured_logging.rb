# Structured logging concern for controllers and jobs
module StructuredLogging
  extend ActiveSupport::Concern

  private

  def log_info(message, extra = {})
    Rails.logger.info(log_entry("INFO", message, extra))
  end

  def log_error(message, extra = {})
    Rails.logger.error(log_entry("ERROR", message, extra))
  end

  def log_warn(message, extra = {})
    Rails.logger.warn(log_entry("WARN", message, extra))
  end

          def log_entry(level, message, extra = {})
            entry = {
              timestamp: Time.current.iso8601,
              level: level,
              message: message,
              request_id: current_request_id,
              user_id: respond_to?(:current_user) ? current_user&.id : nil,
              controller: self.class.name,
              action: respond_to?(:action_name) ? action_name : nil
            }.merge(extra).compact

            entry.to_json
          end

  def current_request_id
    return nil unless respond_to?(:request) && request
    request.env["REQUEST_ID"]
  end

  def sanitize_params(params)
    # Remove sensitive data from logs
    sanitized = params.dup
    sanitized.delete(:password)
    sanitized.delete(:password_confirmation)
    sanitized.delete(:token)
    sanitized.delete(:secret)
    sanitized
  end
end
