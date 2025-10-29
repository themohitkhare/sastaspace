import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="loading"
export default class extends Controller {
  static targets = ["spinner", "content"]

  connect() {
    // Show loading state when Turbo starts a visit
    document.addEventListener("turbo:before-visit", this.showLoading.bind(this))
    document.addEventListener("turbo:visit", this.showLoading.bind(this))
    
    // Hide loading state when Turbo completes
    document.addEventListener("turbo:load", this.hideLoading.bind(this))
    document.addEventListener("turbo:frame-load", this.hideLoading.bind(this))
  }

  disconnect() {
    document.removeEventListener("turbo:before-visit", this.showLoading.bind(this))
    document.removeEventListener("turbo:visit", this.showLoading.bind(this))
    document.removeEventListener("turbo:load", this.hideLoading.bind(this))
    document.removeEventListener("turbo:frame-load", this.hideLoading.bind(this))
  }

  showLoading() {
    if (this.hasSpinnerTarget) {
      this.spinnerTarget.classList.remove("hidden")
    }
    if (this.hasContentTarget) {
      this.contentTarget.classList.add("opacity-50")
    }
  }

  hideLoading() {
    if (this.hasSpinnerTarget) {
      this.spinnerTarget.classList.add("hidden")
    }
    if (this.hasContentTarget) {
      this.contentTarget.classList.remove("opacity-50")
    }
  }
}

