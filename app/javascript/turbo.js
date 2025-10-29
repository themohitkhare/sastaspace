// Turbo configuration for SPA-like navigation
import { Turbo } from "@hotwired/turbo-rails"

// Configure Turbo progress bar
Turbo.session.driver = Turbo.session.CacheDriver

// Add request ID to Turbo requests for better debugging
document.addEventListener("turbo:before-fetch-request", (event) => {
  const requestId = document.querySelector('meta[name="csrf-token"]')?.content || ""
  if (requestId) {
    event.detail.fetchOptions.headers["X-Request-ID"] = requestId
  }
})

// Handle Turbo form submissions
document.addEventListener("turbo:submit-end", (event) => {
  if (event.detail.success) {
    // Optional: Scroll to top on successful form submission
    // window.scrollTo({ top: 0, behavior: "smooth" })
  }
})

export default Turbo

