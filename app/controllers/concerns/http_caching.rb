# HTTP Caching Support
# Provides ETag and Last-Modified headers for conditional GET requests
# Implements RFC 7232 conditional requests (If-None-Match, If-Modified-Since)
require "digest"

module HttpCaching
  extend ActiveSupport::Concern

  private

  # Set ETag and Last-Modified headers based on resource(s)
  # @param resource [ActiveRecord::Base, ActiveRecord::Relation, Array] The resource(s) to cache
  # @param options [Hash] Additional options
  #   - :public [Boolean] Whether the response can be cached by public caches (default: false)
  #   - :must_revalidate [Boolean] Whether caches must revalidate (default: true)
  def set_cache_headers(resource, options = {})
    etag_value = generate_etag(resource)
    last_modified_value = get_last_modified(resource)

    # Set ETag header
    response.headers["ETag"] = %("#{etag_value}") if etag_value.present?

    # Set Last-Modified header
    response.headers["Last-Modified"] = last_modified_value.httpdate if last_modified_value.present?

    # Set Cache-Control header
    cache_control = []
    cache_control << (options[:public] ? "public" : "private")
    cache_control << "must-revalidate" if options.fetch(:must_revalidate, true)
    cache_control << "max-age=0" # Force revalidation
    response.headers["Cache-Control"] = cache_control.join(", ")

    # Handle conditional requests
    if request.fresh?(response)
      head :not_modified
      return true
    end

    false
  end

  # Generate ETag from resource(s)
  # Uses updated_at timestamp and resource checksum
  def generate_etag(resource)
    if resource.is_a?(ActiveRecord::Base)
      # Single resource: use updated_at (with microseconds) and id
      # Include microseconds to ensure ETag changes even within the same second
      timestamp = resource.updated_at.to_f
      # Also include a hash of key attributes to ensure changes are detected
      key_attrs = resource.attributes.slice("name", "title", "description").to_json
      checksum = Digest::MD5.hexdigest("#{resource.class.name}-#{resource.id}-#{timestamp}-#{key_attrs}")
      "#{resource.class.name.downcase}-#{resource.id}-#{checksum[0..7]}"
    elsif resource.is_a?(Array)
      # Array of resources: combine ETags (check Array before Relation to avoid conflicts)
      etags = resource.map { |r| generate_etag(r) }.compact
      return nil if etags.empty?
      Digest::MD5.hexdigest(etags.join("-"))[0..15]
    elsif resource.respond_to?(:maximum) && resource.respond_to?(:klass)
      # ActiveRecord::Relation: use max updated_at
      max_updated = resource.maximum(:updated_at)
      return nil unless max_updated
      timestamp = max_updated.to_i
      count = resource.count
      checksum = Digest::MD5.hexdigest("#{resource.klass.name}-#{count}-#{timestamp}")
      "#{resource.klass.name.downcase}-collection-#{checksum[0..7]}"
    else
      nil
    end
  end

  # Get Last-Modified timestamp from resource(s)
  def get_last_modified(resource)
    if resource.is_a?(ActiveRecord::Base)
      resource.updated_at
    elsif resource.is_a?(Array) && resource.any?
      # Array of resources: get max updated_at (check Array before Relation to avoid conflicts)
      resource.map { |r| r.respond_to?(:updated_at) ? r.updated_at : nil }.compact.max
    elsif resource.respond_to?(:maximum) && resource.respond_to?(:klass)
      # ActiveRecord::Relation: use max updated_at
      resource.maximum(:updated_at)
    else
      nil
    end
  end

  # Check if request is fresh (304 Not Modified)
  # This is handled by Rails' request.fresh? method when ETag/Last-Modified are set
  def fresh_request?(resource)
    etag_value = generate_etag(resource)
    last_modified_value = get_last_modified(resource)

    # Set headers temporarily to check freshness
    response.headers["ETag"] = %("#{etag_value}") if etag_value.present?
    response.headers["Last-Modified"] = last_modified_value.httpdate if last_modified_value.present?

    request.fresh?(response)
  end
end
