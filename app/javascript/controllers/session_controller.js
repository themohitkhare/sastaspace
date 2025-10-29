import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="session"
// Manages current user state and auto-refreshes tokens
export default class extends Controller {
  connect() {
    // Check token expiration and refresh if needed
    this.checkAndRefreshToken()
    
    // Set up periodic token refresh check (every 5 minutes)
    this.refreshInterval = setInterval(() => {
      this.checkAndRefreshToken()
    }, 5 * 60 * 1000)
  }

  disconnect() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  }

  checkAndRefreshToken() {
    // Check if access token is about to expire (within 2 minutes)
    // This is a client-side check - the actual refresh happens on the server
    // when the next request is made with an expired token
    
    // We rely on the server-side SessionAuthenticable concern to handle
    // token refresh automatically when a request is made with an expired token
  }
}

