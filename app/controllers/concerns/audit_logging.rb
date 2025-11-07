# Audit logging concern for security events
module AuditLogging
  extend ActiveSupport::Concern

  private

  # Log security events for audit trail
  def log_security_event(event_type, details = {})
    audit_entry = {
      timestamp: Time.current.iso8601,
      event_type: event_type,
      user_id: current_user&.id,
      ip_address: request.remote_ip,
      user_agent: request.user_agent,
      request_id: request.env["REQUEST_ID"],
      details: details
    }

    # Log to Rails logger (structured JSON)
    Rails.logger.info("[AUDIT] #{audit_entry.to_json}")

    # In production, you might want to send to a separate audit log service
    # or write to a dedicated audit table
  end

  # Log authentication events
  def log_auth_event(event_type, details = {})
    log_security_event("auth:#{event_type}", details)
  end

  # Log data access events
  def log_data_access_event(resource_type, resource_id, action, details = {})
    log_security_event("data_access", {
      resource_type: resource_type,
      resource_id: resource_id,
      action: action
    }.merge(details))
  end

  # Log data modification events
  def log_data_modification_event(resource_type, resource_id, action, details = {})
    log_security_event("data_modification", {
      resource_type: resource_type,
      resource_id: resource_id,
      action: action
    }.merge(details))
  end
end
