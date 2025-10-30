// Configure your import map in config/importmap.rb. Read more: https://github.com/rails/importmap-rails
import "turbo"
import "controllers"
import "@rails/activestorage"

// Start Active Storage for direct uploads
window.addEventListener("DOMContentLoaded", () => {
  if (window.ActiveStorage && typeof window.ActiveStorage.start === "function") {
    window.ActiveStorage.start();
  }
});
