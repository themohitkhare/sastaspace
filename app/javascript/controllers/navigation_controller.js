import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="navigation"
export default class extends Controller {
  static targets = ["mobileMenu"]

  toggle() {
    this.mobileMenuTarget.classList.toggle("hidden")
  }

  close() {
    this.mobileMenuTarget.classList.add("hidden")
  }
}

