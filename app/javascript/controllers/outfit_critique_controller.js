import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["results", "loading", "content", "button"]
  static values = { outfitId: Number }

  analyze() {
    this.showLoading()
    
    fetch(`/api/v1/outfits/${this.outfitIdValue}/critique`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        this.renderResult(data.data)
      } else {
        this.showError(data.error?.message || "Analysis failed")
      }
    })
    .catch(error => {
      console.error("Critique error:", error)
      this.showError("Network error. Please try again.")
    })
    .finally(() => {
      this.hideLoading()
    })
  }

  renderResult(data) {
    this.contentTarget.classList.remove("hidden")
    this.resultsTarget.innerHTML = `
      <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-bold text-gray-900 dark:text-white">Stylist's Verdict</h3>
          <span class="px-3 py-1 bg-primary-100 text-primary-800 rounded-full font-bold text-sm">
            Score: ${data.score}/100
          </span>
        </div>
        
        <p class="text-gray-700 dark:text-gray-300 mb-4 italic">"${this.escapeHtml(data.summary)}"</p>
        
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-green-700 dark:text-green-400 mb-2 flex items-center gap-2">
              <span>✅</span> Strengths
            </h4>
            <ul class="space-y-1 text-sm text-gray-600 dark:text-gray-400 list-disc list-inside">
              ${(data.strengths || []).map(s => `<li>${this.escapeHtml(s)}</li>`).join('')}
            </ul>
          </div>
          
          <div>
            <h4 class="font-semibold text-blue-700 dark:text-blue-400 mb-2 flex items-center gap-2">
              <span>💡</span> Improvements
            </h4>
            <ul class="space-y-1 text-sm text-gray-600 dark:text-gray-400 list-disc list-inside">
              ${(data.improvements || []).map(s => `<li>${this.escapeHtml(s)}</li>`).join('')}
            </ul>
          </div>
        </div>
      </div>
    `
    // Scroll to results
    this.contentTarget.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  showLoading() {
    this.loadingTarget.classList.remove("hidden")
    this.buttonTarget.disabled = true
    this.buttonTarget.classList.add("opacity-50", "cursor-not-allowed")
  }

  hideLoading() {
    this.loadingTarget.classList.add("hidden")
    this.buttonTarget.disabled = false
    this.buttonTarget.classList.remove("opacity-50", "cursor-not-allowed")
  }

  showError(message) {
    this.contentTarget.classList.remove("hidden")
    this.resultsTarget.innerHTML = `
      <div class="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
        <p class="font-medium">Analysis Failed</p>
        <p class="text-sm">${this.escapeHtml(message)}</p>
      </div>
    `
  }

  escapeHtml(str) {
    if (!str) return ''
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
  }
}

