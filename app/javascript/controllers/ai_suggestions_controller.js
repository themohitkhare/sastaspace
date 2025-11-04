import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["list", "loading", "error"]

  static values = {
    outfitId: Number
  }

  connect() {
    // Listen for suggestions requested from outfit builder
    document.addEventListener("outfit-builder:suggestions-requested", this.handleSuggestionsRequest.bind(this))
  }

  disconnect() {
    document.removeEventListener("outfit-builder:suggestions-requested", this.handleSuggestionsRequest.bind(this))
    if (this.requestTimeout) {
      clearTimeout(this.requestTimeout)
    }
  }

  async handleSuggestionsRequest(event) {
    const items = event.detail.items || []
    if (!items || items.length === 0) {
      this.clearSuggestions()
      return
    }

    // Small delay to avoid too many requests
    if (this.requestTimeout) {
      clearTimeout(this.requestTimeout)
    }
    
    this.requestTimeout = setTimeout(() => {
      this.fetchSuggestions(items)
    }, 500) // Debounce: wait 500ms after last change
  }

  async fetchSuggestions(selectedItems) {
    this.showLoading()
    this.hideError()

    try {
      // If we have an outfit ID, use the suggestions endpoint
      if (this.hasOutfitIdValue && this.outfitIdValue) {
        const excludeIds = selectedItems.map(item => item.id).filter(id => id)
        const url = `/api/v1/outfits/${this.outfitIdValue}/suggestions?limit=6${excludeIds.length > 0 ? `&exclude_ids[]=${excludeIds.join('&exclude_ids[]=')}` : ''}`
        
        const response = await fetch(url, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
          },
          credentials: "include"
        })

        const data = await response.json()
        if (data.success && data.data.items) {
          this.renderSuggestions(data.data.items)
          return
        }
      }

      // For new outfits (no ID yet), use semantic search based on selected items
      await this.fetchSuggestionsForNewOutfit(selectedItems)

    } catch (error) {
      console.error("Error fetching suggestions:", error)
      this.showError("Failed to load suggestions. Please try again.")
    } finally {
      this.hideLoading()
    }
  }

  async fetchSuggestionsForNewOutfit(selectedItems) {
    if (selectedItems.length === 0) {
      this.showEmptyState()
      return
    }

    try {
      // Strategy: Use semantic search to find complementary items
      // Build a query based on what's missing from the outfit
      const existingCategories = selectedItems.map(item => item.category?.toLowerCase() || "").filter(c => c)
      
      // Determine what's missing
      const hasTop = existingCategories.some(cat => cat.includes("top") || cat.includes("shirt") || cat.includes("blouse"))
      const hasBottom = existingCategories.some(cat => cat.includes("bottom") || cat.includes("jean") || cat.includes("pant") || cat.includes("skirt"))
      const hasShoe = existingCategories.some(cat => cat.includes("shoe") || cat.includes("boot") || cat.includes("sneaker"))
      
      const queries = []
      if (!hasBottom && hasTop) queries.push("jeans pants bottoms")
      if (!hasShoe) queries.push("shoes boots sneakers")
      if (!hasTop && hasBottom) queries.push("tops shirts blouses")
      if (hasTop && hasBottom) queries.push("accessories bags jewelry")
      
      // If no specific query, use a general one based on existing items
      const searchQuery = queries.length > 0 
        ? queries.join(" ") 
        : selectedItems.map(item => item.category || item.name).join(" ")
      
      // Use semantic search
      const response = await fetch(`/api/v1/inventory_items/semantic_search?q=${encodeURIComponent(searchQuery)}&limit=6`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include"
      })

      const data = await response.json()
      if (data.success && data.data.inventory_items) {
        // Filter out items already selected
        const selectedIds = selectedItems.map(item => parseInt(item.id)).filter(id => !isNaN(id))
        const suggestions = data.data.inventory_items
          .filter(item => !selectedIds.includes(item.id))
          .slice(0, 6) // Limit to 6 suggestions
        
        if (suggestions.length > 0) {
          this.renderSuggestions(suggestions)
        } else {
          this.showEmptyState()
        }
      } else {
        // Fallback: Get similar items for the first selected item
        await this.fetchSimilarItemsFallback(selectedItems)
      }

    } catch (error) {
      console.error("Error fetching suggestions for new outfit:", error)
      // Fallback to similar items
      await this.fetchSimilarItemsFallback(selectedItems)
    }
  }

  async fetchSimilarItemsFallback(selectedItems) {
    if (selectedItems.length === 0) {
      this.showEmptyState()
      return
    }

    try {
      const allSuggestions = []
      const selectedIds = selectedItems.map(item => parseInt(item.id)).filter(id => !isNaN(id))

      // Get similar items for the first selected item
      const primaryItem = selectedItems[0]
      const response = await fetch(`/api/v1/inventory_items/${primaryItem.id}/similar?limit=6`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include"
      })

      const data = await response.json()
      if (data.success && data.data.similar_items) {
        const suggestions = data.data.similar_items
          .filter(item => !selectedIds.includes(item.id))
          .slice(0, 6)
        
        if (suggestions.length > 0) {
          this.renderSuggestions(suggestions)
        } else {
          this.showEmptyState()
        }
      } else {
        this.showEmptyState()
      }
    } catch (error) {
      console.error("Error in fallback suggestions:", error)
      this.showError("Unable to load suggestions.")
    }
  }


  renderSuggestions(items) {
    if (!this.hasListTarget) return

    if (items.length === 0) {
      this.showEmptyState()
      return
    }

    // SVG placeholder as data URI (clothing icon)
    const placeholderImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23e5e7eb'/%3E%3Cg fill='%239ca3af'%3E%3Cpath d='M60 70h80v80H60z'/%3E%3Ccircle cx='100' cy='95' r='12'/%3E%3Cpath d='M70 135l30-25 20 15 20-20 30 30H70z'/%3E%3C/g%3E%3C/svg%3E"

    // Escape HTML attributes to prevent XSS and syntax errors
    const escapeHtml = (str) => {
      if (!str) return ''
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
    }
    
    // Escape JavaScript strings (for use in inline event handlers)
    const escapeJs = (str) => {
      if (!str) return ''
      return String(str)
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r')
    }

    this.listTarget.innerHTML = `
      <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
        ${items.map(item => {
          const imageUrl = item.images?.primary?.urls?.thumb || item.images?.primary?.urls?.medium || item.images?.primary?.urls?.original || placeholderImage
          const categoryName = item.category?.name || 'Item'
          
          const escapedImageUrl = escapeHtml(imageUrl)
          const escapedPlaceholder = escapeHtml(placeholderImage)
          const jsEscapedPlaceholder = escapeJs(placeholderImage)
          const escapedItemName = escapeHtml(item.name)
          const escapedCategoryName = escapeHtml(categoryName)
          
          return `
            <div 
              class="border rounded-lg p-3 cursor-pointer hover:shadow-md transition-shadow bg-white dark:bg-gray-700"
              data-action="click->ai-suggestions#addSuggestion"
              data-item-id="${item.id}"
              data-item-name="${escapedItemName}"
              data-item-category="${escapedCategoryName}"
              data-item-image="${escapedImageUrl}"
            >
              <img 
                src="${escapedImageUrl}" 
                alt="${escapedItemName}"
                class="w-full h-20 object-cover rounded mb-2 bg-gray-100 dark:bg-gray-700"
                onerror="this.src='${jsEscapedPlaceholder}'"
              />
              <div class="text-xs font-medium text-gray-900 dark:text-white truncate">${escapedItemName}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">${escapedCategoryName}</div>
              <button 
                type="button"
                class="mt-2 w-full px-2 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700"
                data-action="click->ai-suggestions#addSuggestion"
                data-item-id="${item.id}"
                data-item-name="${escapedItemName}"
                data-item-category="${escapedCategoryName}"
                data-item-image="${escapedImageUrl}"
              >
                Add to Outfit
              </button>
            </div>
          `
        }).join('')}
      </div>
    `
  }

  addSuggestion(event) {
    const itemElement = event.currentTarget.closest('[data-item-id]')
    if (!itemElement) return

    const itemData = {
      id: itemElement.dataset.itemId,
      name: itemElement.dataset.itemName,
      category: itemElement.dataset.itemCategory,
      image_url: itemElement.dataset.itemImage
    }

    // Dispatch event to outfit builder to add the item
    this.dispatch("item-suggested", {
      detail: itemData,
      target: document.querySelector('[data-controller*="outfit-builder"]')
    })
  }

  showEmptyState() {
    if (!this.hasListTarget) return
    this.listTarget.innerHTML = `
      <div class="text-center py-8 text-gray-500 dark:text-gray-400">
        <p class="text-sm">No suggestions available yet.</p>
        <p class="text-xs mt-1">Add more items to your outfit to get AI-powered suggestions.</p>
      </div>
    `
  }

  clearSuggestions() {
    if (!this.hasListTarget) return
    this.listTarget.innerHTML = `
      <div class="text-center py-8 text-gray-500 dark:text-gray-400">
        <p class="text-sm">Start building your outfit to see AI suggestions.</p>
      </div>
    `
  }

  showLoading() {
    if (this.hasLoadingTarget) {
      this.loadingTarget.classList.remove("hidden")
    }
    if (this.hasListTarget) {
      this.listTarget.innerHTML = `
        <div class="text-center py-8">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p class="mt-2 text-sm text-gray-500">Loading suggestions...</p>
        </div>
      `
    }
  }

  hideLoading() {
    if (this.hasLoadingTarget) {
      this.loadingTarget.classList.add("hidden")
    }
  }

  showError(message) {
    if (this.hasErrorTarget) {
      this.errorTarget.textContent = message
      this.errorTarget.classList.remove("hidden")
    }
  }

  hideError() {
    if (this.hasErrorTarget) {
      this.errorTarget.classList.add("hidden")
    }
  }
}
