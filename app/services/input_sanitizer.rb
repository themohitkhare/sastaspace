# Input sanitization service for user-generated content
# Prevents XSS attacks and sanitizes user input
class InputSanitizer
  # HTML tags to allow (for rich text content)
  ALLOWED_TAGS = %w[p br strong em u ol ul li a].freeze
  ALLOWED_ATTRIBUTES = { "a" => %w[href] }.freeze

  # Sanitize HTML content (for descriptions, notes, etc.)
  def self.sanitize_html(html_string)
    return nil if html_string.blank?

    # Use Rails' built-in sanitize helper
    ActionController::Base.helpers.sanitize(
      html_string,
      tags: ALLOWED_TAGS,
      attributes: ALLOWED_ATTRIBUTES
    )
  end

  # Sanitize plain text (removes HTML, scripts, etc.)
  def self.sanitize_text(text)
    return nil if text.blank?

    # Remove HTML tags
    text = ActionController::Base.helpers.strip_tags(text)
    # Remove script tags and event handlers
    text = text.gsub(/<script[^>]*>.*?<\/script>/mi, "")
    text = text.gsub(/on\w+\s*=\s*["'][^"']*["']/i, "")
    # Trim whitespace
    text.strip
  end

  # Sanitize file name (removes path traversal, special chars)
  def self.sanitize_filename(filename)
    return nil if filename.blank?

    # Remove path components
    filename = File.basename(filename)
    # Remove special characters except dots, dashes, underscores
    filename = filename.gsub(/[^a-zA-Z0-9._-]/, "_")
    # Limit length
    filename[0..255]
  end

  # Sanitize email (basic validation)
  def self.sanitize_email(email)
    return nil if email.blank?

    email.strip.downcase
  end

  # Sanitize URL (for links)
  def self.sanitize_url(url)
    return nil if url.blank?

    # Only allow http, https protocols
    sanitized = url.strip
    return nil unless sanitized.match?(/\Ahttps?:\/\//i)

    sanitized
  end
end
