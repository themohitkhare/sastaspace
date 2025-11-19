# ActiveStorage Configuration
# This file configures how ActiveStorage handles image variants

# VIPS is now installed and will be used for image variant processing
# VIPS is faster and more memory-efficient than ImageMagick
#
# Installation verified: vips-8.12.1

# Use VIPS for both development and production
Rails.application.config.active_storage.variant_processor = :vips

# Fallback: If VIPS fails, the serializer will use original images
# This provides graceful degradation

# In development, ensure Active Storage URLs use dev.sastaspace.com with HTTPS
# This matches the Cloudflare proxy setup
if Rails.env.development?
  Rails.application.config.after_initialize do
    # Ensure Active Storage uses dev.sastaspace.com with HTTPS
    # This is handled by default_url_options in development.rb, but we ensure it here too
    ActiveSupport.on_load(:active_storage_blob) do
      # The default_url_options configuration in development.rb should handle this,
      # but we ensure ActiveStorage::Current respects it
      ActiveStorage::Current.url_options = Rails.application.routes.default_url_options.merge(
        host: "dev.sastaspace.com",
        protocol: "https"
      )
    end
  end
end
