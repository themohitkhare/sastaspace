# Be sure to restart your server when you modify this file.

# Version of your assets, change this if you want to expire all your assets.
Rails.application.config.assets.version = "1.0"

# Exclude app/javascript from Sprockets - it's handled by importmap-rails
# This prevents Sprockets from trying to precompile JavaScript files
Rails.application.config.assets.paths.delete(Rails.root.join("app/javascript").to_s)

# Add additional assets to the asset load path.
# Rails.application.config.assets.paths << Emoji.images_path

# Precompile assets
# Note: JavaScript in app/javascript is handled by importmap-rails, not Sprockets
# Placeholder JS files are included here to satisfy Sprockets precompilation (actual JS via importmap)
Rails.application.config.assets.precompile += %w[
  tailwind.css
  application.css
  application.js
  turbo.js
  inter-font.css
  controllers/application.js
  controllers/index.js
  controllers/ai_progress_controller.js
  controllers/ai_suggestions_controller.js
  controllers/auth_controller.js
  controllers/category_picker_controller.js
  controllers/color_analysis_controller.js
  controllers/dark_mode_controller.js
  controllers/flash_controller.js
  controllers/form_wizard_controller.js
  controllers/hello_controller.js
  controllers/image_upload_controller.js
  controllers/inventory_controller.js
  controllers/inventory_creation_analyzer_controller.js
  controllers/loading_controller.js
  controllers/navigation_controller.js
  controllers/outfit_builder_controller.js
  controllers/outfit_gallery_controller.js
  controllers/outfit_photo_analyzer_controller.js
  controllers/session_controller.js
  controllers/stock_photo_extraction_controller.js
]
