import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["outfitsGrid", "filters", "searchInput"]

  connect() {
    // Initialize filters from URL params
    this.updateFiltersFromURL()
  }

  applyFilters(event) {
    event.preventDefault()
    this.submitFilters()
  }

  submitFilters() {
    // Build filter params from form
    const form = this.element.querySelector("form[data-outfit-gallery-target='filters']")
    if (!form) return

    const formData = new FormData(form)
    const params = new URLSearchParams()
    
    // Add active filters
    const occasion = formData.get("occasion")
    if (occasion) params.set("occasion", occasion)
    
    const favorite = formData.get("favorite")
    if (favorite === "on") params.set("favorite", "true")
    
    const dateRange = formData.get("date_range")
    if (dateRange) params.set("date_range", dateRange)
    
    const sort = formData.get("sort")
    if (sort) params.set("sort", sort)
    
    const search = formData.get("search")
    if (search) params.set("search", search)

    // Reload with filters using Turbo
    const url = window.location.pathname + (params.toString() ? `?${params.toString()}` : "")
    Turbo.visit(url)
  }

  clearFilters() {
    // Reset form and reload
    const form = this.element.querySelector("form[data-outfit-gallery-target='filters']")
    if (form) {
      form.reset()
    }
    Turbo.visit(window.location.pathname)
  }

  handleSearch(event) {
    // Debounce search
    clearTimeout(this.searchTimeout)
    this.searchTimeout = setTimeout(() => {
      this.submitFilters()
    }, 500)
  }

  updateFiltersFromURL() {
    const urlParams = new URLSearchParams(window.location.search)
    const form = this.element.querySelector("form[data-outfit-gallery-target='filters']")
    if (!form) return

    // Update form inputs from URL params
    const occasion = urlParams.get("occasion")
    if (occasion) {
      const occasionSelect = form.querySelector('[name="occasion"]')
      if (occasionSelect) occasionSelect.value = occasion
    }

    const favorite = urlParams.get("favorite")
    if (favorite === "true") {
      const favoriteCheckbox = form.querySelector('[name="favorite"]')
      if (favoriteCheckbox) favoriteCheckbox.checked = true
    }

    const dateRange = urlParams.get("date_range")
    if (dateRange) {
      const dateRangeSelect = form.querySelector('[name="date_range"]')
      if (dateRangeSelect) dateRangeSelect.value = dateRange
    }

    const sort = urlParams.get("sort")
    if (sort) {
      const sortSelect = form.querySelector('[name="sort"]')
      if (sortSelect) sortSelect.value = sort
    }

    const search = urlParams.get("search")
    if (search) {
      const searchInput = form.querySelector('[name="search"]')
      if (searchInput) searchInput.value = search
    }
  }
}
