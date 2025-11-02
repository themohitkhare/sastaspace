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

