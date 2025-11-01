import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = [
    "canvas",
    "itemSelector",
    "selectedItems",
    "completenessScore",
    "categoryTabs",
    "itemsGrid",
    "searchInput",
    "colorAnalysis"
  ]

  static values = {
    userId: Number
  }

  connect() {
    this.selectedItems = [] // Array of {id, name, category, image_url}
    this.currentCategory = null
    this.inventoryItems = []
    this.fetchInventoryItems()
    this.setupCanvas()
    
    // Listen for AI suggestions
    this.element.addEventListener("ai-suggestions:item-suggested", this.handleItemSuggested.bind(this))
  }

  setupCanvas() {
    // Make canvas a drop zone
    if (this.hasCanvasTarget) {
      this.canvasTarget.addEventListener("dragover", this.handleDragOver.bind(this))
      this.canvasTarget.addEventListener("drop", this.handleDrop.bind(this))
      this.canvasTarget.addEventListener("dragleave", this.handleDragLeave.bind(this))
    }
  }

  async fetchInventoryItems(categoryId = null) {
    try {
      const url = categoryId
        ? `/api/v1/inventory_items?category_id=${categoryId}&per_page=100`
        : `/api/v1/inventory_items?per_page=100`
      
      const response = await fetch(url, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')?.content || ""
        },
        credentials: "include"
      })

      if (!response.ok) {
        console.error("Failed to fetch inventory items:", response.status, response.statusText)
        this.itemsGridTarget.innerHTML = '<div class="text-red-500 text-center py-8">Failed to load items</div>'
        return
      }

      const data = await response.json()
      if (data.success) {
        this.inventoryItems = data.data.inventory_items || []
        this.renderItemsGrid()
      } else {
        console.error("API returned error:", data.error)
        this.itemsGridTarget.innerHTML = '<div class="text-red-500 text-center py-8">Failed to load items</div>'
      }
    } catch (error) {
      console.error("Error fetching inventory items:", error)
      if (this.hasItemsGridTarget) {
        this.itemsGridTarget.innerHTML = '<div class="text-red-500 text-center py-8">Error loading items</div>'
      }
    }
  }

  renderItemsGrid() {
    if (!this.hasItemsGridTarget) return

    if (this.inventoryItems.length === 0) {
      this.itemsGridTarget.innerHTML = '<div class="text-gray-500 text-center py-8">No items found</div>'
      return
    }

    this.itemsGridTarget.innerHTML = this.inventoryItems.map(item => {
      const imageUrl = item.images?.primary?.urls?.thumb || item.images?.primary?.urls?.original || '/placeholder-item.png'
      const categoryName = item.category?.name || 'Uncategorized'
      
      return `
        <div 
          class="border rounded-lg p-2 cursor-move hover:shadow-md transition-shadow bg-white dark:bg-gray-800"
          draggable="true"
          data-item-id="${item.id}"
          data-item-name="${item.name}"
          data-item-category="${categoryName}"
          data-item-image="${imageUrl}"
          data-action="dragstart->outfit-builder#handleDragStart"
        >
          <img 
            src="${imageUrl}" 
            alt="${item.name}"
            class="w-full h-24 object-cover rounded mb-2"
            onerror="this.src='/placeholder-item.png'"
          />
          <div class="text-xs font-medium text-gray-900 dark:text-white truncate">${item.name}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400">${categoryName}</div>
        </div>
      `
    }).join('')
  }

  handleDragStart(event) {
    const itemElement = event.currentTarget
    const itemData = {
      id: itemElement.dataset.itemId,
      name: itemElement.dataset.itemName,
      category: itemElement.dataset.itemCategory,
      image_url: itemElement.dataset.itemImage
    }
    
    event.dataTransfer.setData("application/json", JSON.stringify(itemData))
    event.dataTransfer.effectAllowed = "move"
    event.currentTarget.style.opacity = "0.5"
  }

  handleDragOver(event) {
    event.preventDefault()
    event.dataTransfer.dropEffect = "move"
    this.canvasTarget.classList.add("border-primary-500", "bg-primary-50", "dark:bg-primary-900")
  }

  handleDragLeave(event) {
    this.canvasTarget.classList.remove("border-primary-500", "bg-primary-50", "dark:bg-primary-900")
  }

  handleDrop(event) {
    event.preventDefault()
    this.canvasTarget.classList.remove("border-primary-500", "bg-primary-50", "dark:bg-primary-900")
    
    try {
      const itemData = JSON.parse(event.dataTransfer.getData("application/json"))
      this.addItemToOutfit(itemData)
    } catch (error) {
      console.error("Error handling drop:", error)
    }

    // Reset drag state
    document.querySelectorAll('[draggable="true"]').forEach(el => {
      el.style.opacity = "1"
    })
  }

  addItemToOutfit(itemData) {
    // Check if item already exists
    if (this.selectedItems.find(item => item.id === itemData.id)) {
      return
    }

    this.selectedItems.push(itemData)
    this.renderSelectedItems()
    this.updateCompletenessScore()
    this.updateHiddenField()
    this.updateColorAnalysis()
    this.requestAiSuggestions()
  }

  removeItem(itemId) {
    this.selectedItems = this.selectedItems.filter(item => item.id !== itemId)
    this.renderSelectedItems()
    this.updateCompletenessScore()
    this.updateHiddenField()
    this.updateColorAnalysis()
    this.requestAiSuggestions()
  }

  renderSelectedItems() {
    if (!this.hasSelectedItemsTarget) return

    if (this.selectedItems.length === 0) {
      this.selectedItemsTarget.innerHTML = `
        <div class="text-center py-12 text-gray-500 dark:text-gray-400">
          <svg class="mx-auto h-12 w-12 mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p>Drag items here or select from below</p>
        </div>
      `
      return
    }

    this.selectedItemsTarget.innerHTML = this.selectedItems.map((item, index) => `
      <div class="relative group border rounded-lg p-3 bg-white dark:bg-gray-800" data-item-id="${item.id}">
        <button
          type="button"
          class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600"
          data-action="click->outfit-builder#removeItem"
          data-item-id="${item.id}"
          aria-label="Remove item"
        >
          ×
        </button>
        <img 
          src="${item.image_url}" 
          alt="${item.name}"
          class="w-full h-24 object-cover rounded mb-2"
          onerror="this.src='/placeholder-item.png'"
        />
        <div class="text-sm font-medium text-gray-900 dark:text-white truncate">${item.name}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">${item.category}</div>
      </div>
    `).join('')
  }

  updateCompletenessScore() {
    if (!this.hasCompletenessScoreTarget) return

    // Calculate completeness based on essential categories
    const categories = this.selectedItems.map(item => item.category.toLowerCase())
    const essentialCategories = ['tops', 'bottoms', 'shoes']
    const hasEssential = essentialCategories.some(cat => 
      categories.some(itemCat => itemCat.includes(cat))
    )

    const score = this.calculateCompletenessScore()
    const percentage = Math.round(score * 100)

    this.completenessScoreTarget.innerHTML = `
      <div class="flex items-center space-x-2">
        <div class="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div 
            class="bg-primary-600 h-2 rounded-full transition-all duration-300"
            style="width: ${percentage}%"
          ></div>
        </div>
        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">${percentage}%</span>
      </div>
      <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">${this.getCompletenessMessage(score)}</p>
    `
  }

  calculateCompletenessScore() {
    const categories = this.selectedItems.map(item => item.category.toLowerCase())
    
    // Essential items
    const hasTop = categories.some(cat => cat.includes('top') || cat.includes('shirt') || cat.includes('blouse'))
    const hasBottom = categories.some(cat => cat.includes('bottom') || cat.includes('pant') || cat.includes('skirt'))
    const hasShoes = categories.some(cat => cat.includes('shoe') || cat.includes('boot') || cat.includes('sandal'))
    
    let score = 0
    if (hasTop) score += 0.3
    if (hasBottom) score += 0.3
    if (hasShoes) score += 0.2
    
    // Additional items boost score
    const accessoryCount = categories.filter(cat => 
      cat.includes('accessory') || cat.includes('bag') || cat.includes('jewelry')
    ).length
    score += Math.min(accessoryCount * 0.1, 0.2) // Max 0.2 for accessories
    
    return Math.min(score, 1.0)
  }

  getCompletenessMessage(score) {
    if (score >= 0.8) return "Complete outfit! ✓"
    if (score >= 0.5) return "Almost there - add shoes or accessories"
    if (score >= 0.3) return "Good start - add more items"
    return "Start adding items to build your outfit"
  }

  updateHiddenField() {
    const hiddenField = this.element.querySelector('input[name="outfit[inventory_item_ids][]"]')
    if (hiddenField && hiddenField.parentElement) {
      // Remove all existing hidden fields
      hiddenField.parentElement.querySelectorAll('input[name="outfit[inventory_item_ids][]"]').forEach(el => el.remove())
      
      // Add new hidden fields for each selected item
      this.selectedItems.forEach(item => {
        const input = document.createElement('input')
        input.type = 'hidden'
        input.name = 'outfit[inventory_item_ids][]'
        input.value = item.id
        hiddenField.parentElement.appendChild(input)
      })
    }
  }

  async requestAiSuggestions() {
    if (this.selectedItems.length === 0) return

    // Dispatch event for AI suggestions controller
    const event = new CustomEvent("outfit-builder:suggestions-requested", {
      detail: { items: this.selectedItems },
      bubbles: true
    })
    document.dispatchEvent(event)
  }

  handleItemSuggested(event) {
    const itemData = event.detail
    this.addItemToOutfit(itemData)
  }

  filterByCategory(event) {
    const categoryId = event.currentTarget.dataset.categoryId
    this.currentCategory = categoryId === "all" ? null : categoryId
    this.fetchInventoryItems(this.currentCategory)
    
    // Update active tab
    if (this.hasCategoryTabsTarget) {
      this.categoryTabsTarget.querySelectorAll('button').forEach(btn => {
        btn.classList.remove('bg-primary-600', 'text-white')
        btn.classList.add('bg-gray-200', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-gray-300')
      })
      event.currentTarget.classList.remove('bg-gray-200', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-gray-300')
      event.currentTarget.classList.add('bg-primary-600', 'text-white')
    }
  }

  async searchItems(event) {
    const query = event.target.value.trim()
    
    if (query.length < 2) {
      this.fetchInventoryItems(this.currentCategory)
      return
    }

    try {
      const response = await fetch(`/api/v1/inventory_items/search?q=${encodeURIComponent(query)}&per_page=100`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include"
      })

      const data = await response.json()
      if (data.success) {
        this.inventoryItems = data.data.inventory_items
        this.renderItemsGrid()
      }
    } catch (error) {
      console.error("Error searching items:", error)
    }
  }

  removeItem(event) {
    const itemId = event.currentTarget.dataset.itemId
    this.removeItem(itemId)
  }

  async updateColorAnalysis() {
    if (!this.hasColorAnalysisTarget) return

    if (this.selectedItems.length === 0) {
      this.colorAnalysisTarget.innerHTML = `
        <div class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
          Add items to analyze color coordination
        </div>
      `
      return
    }

    // Extract item IDs for API call
    const itemIds = this.selectedItems.map(item => parseInt(item.id)).filter(id => !isNaN(id))
    
    if (itemIds.length === 0) {
      return
    }

    try {
      const response = await fetch(`/api/v1/outfits/color_analysis?item_ids[]=${itemIds.join('&item_ids[]=')}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include"
      })

      const data = await response.json()
      if (data.success && data.data) {
        this.renderColorAnalysis(data.data)
      }
    } catch (error) {
      console.error("Error fetching color analysis:", error)
      // Silently fail - color analysis is nice-to-have
    }
  }

  renderColorAnalysis(analysis) {
    if (!this.hasColorAnalysisTarget) return

    const score = Math.round(analysis.score * 100)
    const colors = Object.keys(analysis.colors || {})
    const scoreColor = score >= 70 ? "text-green-600" : score >= 50 ? "text-yellow-600" : "text-red-600"
    const barColor = score >= 70 ? "bg-green-600" : score >= 50 ? "bg-yellow-600" : "bg-red-600"

    let html = `
      <div class="space-y-3">
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-gray-900 dark:text-white">Color Coordination</span>
            <span class="text-sm font-bold ${scoreColor}">${score}%</span>
          </div>
          <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div class="${barColor} h-2 rounded-full transition-all duration-300" style="width: ${score}%"></div>
          </div>
        </div>

        <div class="text-sm text-gray-700 dark:text-gray-300">
          ${analysis.feedback || "No feedback available"}
        </div>
    `

    // Show colors detected
    if (colors.length > 0) {
      html += `
        <div>
          <span class="text-xs font-medium text-gray-600 dark:text-gray-400">Colors:</span>
          <div class="flex flex-wrap gap-1 mt-1">
            ${colors.map(color => `
              <span class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded text-gray-700 dark:text-gray-300">
                ${color.charAt(0).toUpperCase() + color.slice(1)}
              </span>
            `).join('')}
          </div>
        </div>
      `
    }

    // Show warnings
    if (analysis.warnings && analysis.warnings.length > 0) {
      html += `
        <div class="text-xs text-yellow-700 dark:text-yellow-400">
          <div class="font-medium mb-1">⚠️ Tips:</div>
          <ul class="list-disc list-inside space-y-1">
            ${analysis.warnings.map(warning => `<li>${warning}</li>`).join('')}
          </ul>
        </div>
      `
    }

    // Show suggestions
    if (analysis.suggestions && analysis.suggestions.length > 0) {
      html += `
        <div class="text-xs text-blue-700 dark:text-blue-400">
          <div class="font-medium mb-1">💡 Suggestions:</div>
          <ul class="list-disc list-inside space-y-1">
            ${analysis.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
          </ul>
        </div>
      `
    }

    html += `</div>`
    this.colorAnalysisTarget.innerHTML = html
  }
}
