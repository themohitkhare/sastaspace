import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = [
    "canvas",
    "itemSelector",
    "selectedItems",
    "categoryTabs",
    "itemsGrid",
    "searchInput",
    "completenessText",
    "completenessRing",
    "completenessIcon",
    "hintsContainer"
  ]

  static values = {
    userId: Number
  }

  connect() {
    this.selectedItems = [] 
    this.currentCategory = null
    this.inventoryItems = []
    this.isInitialized = false
    
    this.initializeExistingItems()
    
    this.fetchInventoryItems().then(() => {
      this.isInitialized = true
    }).catch(() => {
      this.isInitialized = true
    })
    
    this.setupCanvas()
    
    this.element.addEventListener("ai-suggestions:item-suggested", this.handleItemSuggested.bind(this))
    
    const form = this.element.closest('form') || this.element.querySelector('form')
    if (form) {
      form.addEventListener("submit", (event) => {
        this.updateHiddenField()
      }, { capture: true })
    }
    console.log("Outfit Builder connected")
  }

  initializeExistingItems() {
    const hiddenFields = this.element.querySelectorAll('input[name="outfit[inventory_item_ids][]"].existing-outfit-item')
    const existingItemIds = []
    
    hiddenFields.forEach(field => {
      const value = field.value.trim()
      if (value && value !== '') {
        const id = parseInt(value)
        if (!isNaN(id)) existingItemIds.push(id)
      }
    })

    if (existingItemIds.length > 0) {
      this.pendingItemIds = existingItemIds
    }
  }

  setupCanvas() {
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
        }
      })

      if (!response.ok) return

      const data = await response.json()
      if (data.success) {
        this.inventoryItems = data.data.inventory_items || []
        
        if (this.pendingItemIds && this.pendingItemIds.length > 0) {
          this.loadExistingItems(this.pendingItemIds)
          delete this.pendingItemIds
        }
        
        this.renderItemsGrid()
      }
    } catch (error) {
      console.error("Error fetching items:", error)
    }
  }

  renderItemsGrid() {
    if (!this.hasItemsGridTarget) return

    if (this.inventoryItems.length === 0) {
      this.itemsGridTarget.innerHTML = '<div class="text-gray-500 text-center py-8">No items found</div>'
      return
    }

    const placeholderImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23e5e7eb'/%3E%3Cg fill='%239ca3af'%3E%3Cpath d='M60 70h80v80H60z'/%3E%3Ccircle cx='100' cy='95' r='12'/%3E%3Cpath d='M70 135l30-25 20 15 20-20 30 30H70z'/%3E%3C/g%3E%3C/svg%3E"
    
    this.itemsGridTarget.innerHTML = this.inventoryItems.map(item => {
      let imageUrl = placeholderImage
      if (item.images?.primary?.urls) {
        imageUrl = item.images.primary.urls.thumb || item.images.primary.urls.medium || item.images.primary.urls.original || placeholderImage
      }
      
      const escapeHtml = (str) => {
        if (!str) return ''
        return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      }
      
      const escapeJs = (str) => {
        if (!str) return ''
        return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n').replace(/\r/g, '\\r')
      }
      
      const categoryName = item.category?.name || 'Uncategorized'
      const escapedImageUrl = escapeHtml(imageUrl)
      const jsEscapedPlaceholder = escapeJs(placeholderImage)
      const escapedItemName = escapeHtml(item.name)
      const escapedCategoryName = escapeHtml(categoryName)
      
      return `
        <div 
          class="border rounded-lg p-2 cursor-pointer hover:shadow-md transition-shadow bg-white dark:bg-gray-800"
          draggable="true"
          data-item-id="${item.id}"
          data-item-name="${escapedItemName}"
          data-item-category="${escapedCategoryName}"
          data-item-image="${escapedImageUrl}"
          data-action="dragstart->outfit-builder#handleDragStart click->outfit-builder#handleItemClick"
        >
          <img 
            src="${escapedImageUrl}" 
            alt="${escapedItemName}"
            class="w-full h-24 object-cover rounded mb-2 bg-gray-100 dark:bg-gray-700"
            onerror="this.src='${jsEscapedPlaceholder}'"
          />
          <div class="text-xs font-medium text-gray-900 dark:text-white truncate">${escapedItemName}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400">${escapedCategoryName}</div>
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

    document.querySelectorAll('[draggable="true"]').forEach(el => el.style.opacity = "1")
  }

  handleItemClick(event) {
    if (event.target.closest('button')) return
    
    const itemElement = event.currentTarget
    const itemData = {
      id: itemElement.dataset.itemId,
      name: itemElement.dataset.itemName,
      category: itemElement.dataset.itemCategory,
      image_url: itemElement.dataset.itemImage
    }
    
    this.addItemToOutfit(itemData)
  }

  addItemToOutfit(itemData) {
    const normalizeId = (id) => parseInt(id)
    const itemId = normalizeId(itemData.id)
    
    if (this.selectedItems.find(item => normalizeId(item.id) === itemId)) return

    this.selectedItems.push(itemData)
    this.renderSelectedItems()
    this.updateHiddenField()
    this.notifyStateChange()
  }

  removeItem(itemId) {
    const normalizeId = (id) => parseInt(id)
    const id = normalizeId(itemId)
    
    this.selectedItems = this.selectedItems.filter(item => normalizeId(item.id) !== id)
    this.renderSelectedItems()
    this.updateHiddenField()
    this.notifyStateChange()
  }

  notifyStateChange() {
    this.updateCompleteness()
    this.requestAiSuggestions()
    
    // Notify Color Analysis Controller
    const event = new CustomEvent("outfit-builder:items-updated", {
      detail: { itemIds: this.selectedItems.map(i => i.id) },
      bubbles: true
    })
    document.dispatchEvent(event)
  }

  updateCompleteness() {
    if (!this.hasCompletenessTextTarget) return

    // Check categories
    const categories = this.selectedItems.map(i => (i.category || "").toLowerCase())
    const hasTop = categories.some(c => c.includes('top') || c.includes('shirt') || c.includes('blouse') || c.includes('sweater'))
    const hasBottom = categories.some(c => c.includes('bottom') || c.includes('pant') || c.includes('jean') || c.includes('skirt') || c.includes('short'))
    const hasShoe = categories.some(c => c.includes('shoe') || c.includes('boot') || c.includes('sneaker') || c.includes('sandal'))
    
    let score = 0
    const missing = []

    if (hasTop) score += 33
    else missing.push("Top")

    if (hasBottom) score += 33
    else missing.push("Bottom")

    if (hasShoe) score += 34
    else missing.push("Shoes")

    if (score > 99) score = 100

    // Update UI
    this.completenessTextTarget.textContent = `${score}%`
    if (this.hasCompletenessRingTarget) {
      this.completenessRingTarget.setAttribute("stroke-dasharray", `${score}, 100`)
      this.completenessRingTarget.classList.remove("text-red-500", "text-yellow-500", "text-primary-600")
      if (score === 100) this.completenessRingTarget.classList.add("text-primary-600")
      else if (score > 50) this.completenessRingTarget.classList.add("text-yellow-500")
      else this.completenessRingTarget.classList.add("text-red-500")
    }

    if (this.hasCompletenessIconTarget) {
      this.completenessIconTarget.textContent = score === 100 ? "✨" : "👕"
    }

    // Hints
    if (this.hasHintsContainerTarget) {
      if (score === 100) {
        this.hintsContainerTarget.innerHTML = ''
      } else {
        this.hintsContainerTarget.innerHTML = missing.map(m => `
          <div class="bg-blue-50 dark:bg-blue-900/50 text-blue-700 dark:text-blue-200 text-xs px-2 py-1 rounded-md shadow-sm border border-blue-100 dark:border-blue-800 animate-fade-in">
            Add ${m}
          </div>
        `).join('')
      }
    }
  }

  renderSelectedItems() {
    if (!this.hasSelectedItemsTarget) return

    if (this.selectedItems.length === 0) {
      this.selectedItemsTarget.innerHTML = `
        <div class="text-center py-12 text-gray-500 dark:text-gray-400 col-span-full">
          <svg class="mx-auto h-12 w-12 mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p>Drag items here or select from below</p>
        </div>
      `
      return
    }

    const placeholderImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23e5e7eb'/%3E%3Cg fill='%239ca3af'%3E%3Cpath d='M60 70h80v80H60z'/%3E%3Ccircle cx='100' cy='95' r='12'/%3E%3Cpath d='M70 135l30-25 20 15 20-20 30 30H70z'/%3E%3C/g%3E%3C/svg%3E"

    const escapeHtml = (str) => {
      if (!str) return ''
      return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    }
    
    const escapeJs = (str) => {
      if (!str) return ''
      return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n').replace(/\r/g, '\\r')
    }

    this.selectedItemsTarget.innerHTML = this.selectedItems.map((item) => {
      const imageUrl = item.image_url || placeholderImage
      const escapedImageUrl = escapeHtml(imageUrl)
      const jsEscapedPlaceholder = escapeJs(placeholderImage)
      const escapedItemName = escapeHtml(item.name)
      const escapedCategory = escapeHtml(item.category)
      
      return `
      <div class="relative group border rounded-lg p-3 bg-white dark:bg-gray-800 hover:shadow-md transition-shadow" data-item-id="${item.id}">
        <button
          type="button"
          class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600 z-10"
          data-action="click->outfit-builder#handleRemoveItem"
          data-item-id="${item.id}"
          aria-label="Remove item"
        >
          ×
        </button>
        <img 
          src="${escapedImageUrl}" 
          alt="${escapedItemName}"
          class="w-full h-32 object-cover rounded mb-2 bg-gray-100 dark:bg-gray-700"
          onerror="this.src='${jsEscapedPlaceholder}'"
        />
        <div class="text-sm font-medium text-gray-900 dark:text-white truncate">${escapedItemName}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">${escapedCategory}</div>
      </div>
    `
    }).join('')
  }

  loadExistingItems(itemIds) {
    itemIds.forEach(itemId => {
      const item = this.inventoryItems.find(inv => parseInt(inv.id) === parseInt(itemId))
      if (item) {
        const itemData = {
          id: item.id,
          name: item.name || 'Unnamed Item',
          category: item.category?.name || 'Uncategorized',
          image_url: item.images?.primary?.urls?.thumb || 
                     item.images?.primary?.urls?.medium || 
                     item.images?.primary?.urls?.original || 
                     null
        }
        if (!this.selectedItems.find(sel => parseInt(sel.id) === parseInt(itemData.id))) {
          this.selectedItems.push(itemData)
        }
      }
    })
    
    const missingIds = itemIds.filter(id => !this.inventoryItems.find(inv => parseInt(inv.id) === parseInt(id)))
    if (missingIds.length > 0) {
      this.fetchMissingItems(missingIds)
    } else {
      this.renderSelectedItems()
      this.updateHiddenField()
      this.notifyStateChange() // Ensure initial state is correct
    }
  }

  async fetchMissingItems(itemIds) {
    try {
      const promises = itemIds.map(async (id) => {
        try {
          const response = await fetch(`/api/v1/inventory_items/${id}`, {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              "Accept": "application/json",
              "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')?.content || ""
            }
          })
          
          if (response.ok) {
            const data = await response.json()
            if (data.success && data.data) {
              const item = data.data.inventory_item
              const itemData = {
                id: item.id,
                name: item.name || 'Unnamed Item',
                category: item.category?.name || 'Uncategorized',
                image_url: item.images?.primary?.urls?.thumb || 
                           item.images?.primary?.urls?.medium || 
                           item.images?.primary?.urls?.original || 
                           null
              }
              if (!this.selectedItems.find(sel => parseInt(sel.id) === parseInt(itemData.id))) {
                this.selectedItems.push(itemData)
              }
            }
          }
        } catch (error) {
          console.error(`Error fetching item ${id}:`, error)
        }
      })
      
      await Promise.all(promises)
      this.renderSelectedItems()
      this.updateHiddenField()
      this.notifyStateChange()
    } catch (error) {
      console.error("Error fetching missing items:", error)
      this.renderSelectedItems()
      this.updateHiddenField()
      this.notifyStateChange()
    }
  }

  updateHiddenField() {
    const form = this.element.closest('form') || this.element.querySelector('form')
    if (!form) return

    const existingFieldsBefore = Array.from(form.querySelectorAll('input[name="outfit[inventory_item_ids][]"].existing-outfit-item'))
    const existingFieldValues = existingFieldsBefore.map(field => field.value).filter(v => v && v.trim() !== '')
    
    form.querySelectorAll('input[name="outfit[inventory_item_ids][]"]').forEach(el => el.remove())
    
    if (this.selectedItems.length === 0 && existingFieldValues.length > 0 && !this.isInitialized) {
      existingFieldValues.forEach(value => {
        const input = document.createElement('input')
        input.type = 'hidden'
        input.name = 'outfit[inventory_item_ids][]'
        input.value = value
        form.appendChild(input)
      })
      return
    }
    
    this.selectedItems.forEach((item) => {
      const input = document.createElement('input')
      input.type = 'hidden'
      input.name = 'outfit[inventory_item_ids][]'
      input.value = String(item.id)
      form.appendChild(input)
    })
  }

  requestAiSuggestions() {
    if (this.selectedItems.length === 0) return

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
    
    if (this.hasCategoryTabsTarget) {
      this.categoryTabsTarget.querySelectorAll('button').forEach(btn => {
        btn.classList.remove('bg-primary-600', 'text-white')
        btn.classList.add('bg-gray-200', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-gray-300')
      })
      event.currentTarget.classList.remove('bg-gray-200', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-gray-300')
      event.currentTarget.classList.add('bg-primary-600', 'text-white')
    }
  }

  searchItems(event) {
    const query = event.target.value.trim()
    if (query.length < 2) {
      this.fetchInventoryItems(this.currentCategory)
      return
    }

    fetch(`/api/v1/inventory_items/search?q=${encodeURIComponent(query)}&per_page=100`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      }
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        this.inventoryItems = data.data.inventory_items
        this.renderItemsGrid()
      }
    })
  }

  handleRemoveItem(event) {
    event.preventDefault()
    event.stopPropagation()
    const itemId = event.currentTarget.dataset.itemId || event.currentTarget.closest('[data-item-id]')?.dataset.itemId
    if (itemId) {
      this.removeItem(parseInt(itemId))
    }
  }
}
