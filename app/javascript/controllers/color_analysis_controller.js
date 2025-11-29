import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["content", "loading", "scoreBadge", "resultTemplate"]
  static values = { userId: Number }

  connect() {
    // Listen for items update from outfit builder
    this.boundHandleItemsUpdated = this.handleItemsUpdated.bind(this)
    document.addEventListener("outfit-builder:items-updated", this.boundHandleItemsUpdated)
    console.log("Color Analysis controller connected")
  }

  disconnect() {
    document.removeEventListener("outfit-builder:items-updated", this.boundHandleItemsUpdated)
    if (this.analyzeTimeout) clearTimeout(this.analyzeTimeout)
  }

  handleItemsUpdated(event) {
    const itemIds = event.detail.itemIds || []
    console.log("Color Analysis: Items updated", itemIds)

    if (itemIds.length === 0) {
      this.showEmptyState()
      return
    }

    // Debounce analysis request
    if (this.analyzeTimeout) clearTimeout(this.analyzeTimeout)
    this.analyzeTimeout = setTimeout(() => this.analyzeColors(itemIds), 800)
  }

  async analyzeColors(itemIds) {
    this.showLoading()

    try {
      // Build query string manually for array params
      const queryString = itemIds.map(id => `item_ids[]=${id}`).join('&')
      const response = await fetch(`/api/v1/outfits/color_analysis?${queryString}`, {
        method: 'GET',
        headers: {
          "Accept": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        }
      })

      if (!response.ok) throw new Error("Analysis failed")

      const data = await response.json()
      if (data.success) {
        this.renderAnalysis(data.data)
      } else {
        throw new Error(data.error?.message || "Unknown error")
      }
    } catch (error) {
      console.error("Color Analysis Error:", error)
      this.showError()
    } finally {
      this.hideLoading()
    }
  }

  renderAnalysis(data) {
    const template = this.resultTemplateTarget.content.cloneNode(true)
    const scorePct = Math.round((data.score || 0) * 100)
    
    // Update Score
    template.querySelector('[data-field="scoreValue"]').textContent = `${scorePct}%`
    const scoreBar = template.querySelector('[data-field="scoreBar"]')
    scoreBar.style.width = `${scorePct}%`
    
    // Color logic for score bar
    if (scorePct >= 80) scoreBar.classList.add('bg-green-500')
    else if (scorePct >= 50) scoreBar.classList.add('bg-yellow-500')
    else scoreBar.classList.add('bg-red-500')

    // Render Palette
    const paletteContainer = template.querySelector('[data-field="palette"]')
    const colors = Object.keys(data.colors || {})
    
    if (colors.length > 0) {
      colors.forEach(color => {
        const chip = document.createElement('div')
        chip.className = "w-6 h-6 rounded-full border border-gray-200 shadow-sm"
        chip.style.backgroundColor = this.mapColorName(color)
        chip.title = color
        paletteContainer.appendChild(chip)
      })
    } else {
      paletteContainer.innerHTML = '<span class="text-xs text-gray-400 italic">No colors detected</span>'
    }

    // Feedback & Suggestions
    template.querySelector('[data-field="feedback"]').textContent = data.feedback || "Analysis complete"
    
    const suggestionsList = template.querySelector('[data-field="suggestions"]')
    if (data.suggestions && data.suggestions.length > 0) {
      data.suggestions.forEach(suggestion => {
        const li = document.createElement('li')
        li.className = "text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1.5"
        li.innerHTML = `<span class="mt-0.5">•</span><span>${suggestion}</span>`
        suggestionsList.appendChild(li)
      })
    } else {
      suggestionsList.remove()
    }

    // Warnings
    const warningsContainer = template.querySelector('[data-field="warningsContainer"]')
    const warningsList = template.querySelector('[data-field="warnings"]')
    
    if (data.warnings && data.warnings.length > 0) {
      warningsContainer.classList.remove('hidden')
      data.warnings.forEach(warning => {
        const li = document.createElement('li')
        li.textContent = warning
        warningsList.appendChild(li)
      })
    } else {
      warningsContainer.remove()
    }

    // Render to DOM
    this.contentTarget.innerHTML = ''
    this.contentTarget.appendChild(template)

    // Update badge
    this.scoreBadgeTarget.textContent = `${scorePct}%`
    this.scoreBadgeTarget.className = `px-2 py-1 rounded-full text-xs font-medium ${
      scorePct >= 80 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
      scorePct >= 50 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
      'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    }`
    this.scoreBadgeTarget.classList.remove('hidden')
  }

  showEmptyState() {
    this.contentTarget.innerHTML = `
      <div class="text-center py-6 text-gray-500 dark:text-gray-400">
        <p class="text-sm">Add items to see color coordination analysis</p>
      </div>
    `
    this.scoreBadgeTarget.classList.add('hidden')
  }

  showLoading() {
    this.loadingTarget.classList.remove('hidden')
    this.contentTarget.classList.add('opacity-50')
  }

  hideLoading() {
    this.loadingTarget.classList.add('hidden')
    this.contentTarget.classList.remove('opacity-50')
  }

  showError() {
    this.contentTarget.innerHTML = `
      <div class="text-center py-4 text-red-500">
        <p class="text-sm">Unable to analyze colors</p>
      </div>
    `
  }

  mapColorName(name) {
    // Map descriptive names to CSS colors
    const map = {
      'navy': '#000080', 'beige': '#f5f5dc', 'tan': '#d2b48c',
      'burgundy': '#800020', 'charcoal': '#36454f', 'olive': '#808000',
      'cream': '#fffdd0', 'mustard': '#ffdb58', 'teal': '#008080',
      'coral': '#ff7f50', 'lavender': '#e6e6fa', 'khaki': '#f0e68c',
      'salmon': '#fa8072', 'cyan': '#00ffff', 'magenta': '#ff00ff',
      'gold': '#ffd700', 'silver': '#c0c0c0', 'bronze': '#cd7f32'
    }
    return map[name.toLowerCase()] || name.toLowerCase()
  }
}
