import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = [
    "canvas",
    "itemSelector",
    "selectedItems",
    "categoryTabs",
    "itemsGrid",
    "searchInput"
  ]

  static values = {
    userId: Number
  }

  connect() {
    this.selectedItems = [] // Array of {id, name, category, image_url}
    this.currentCategory = null
    this.inventoryItems = []
    this.isInitialized = false // Track if initialization is complete
    
    // Initialize from existing outfit items (for edit page)
    this.initializeExistingItems()
    
    // Fetch inventory items and mark as initialized when done
    this.fetchInventoryItems().then(() => {
      this.isInitialized = true
    }).catch(() => {
      this.isInitialized = true // Mark as initialized even on error
    })
    
    this.setupCanvas()
    
    // Listen for AI suggestions
    this.element.addEventListener("ai-suggestions:item-suggested", this.handleItemSuggested.bind(this))
    
    // Ensure hidden fields are updated before form submission
    // Form is a child of the controller element (not an ancestor)
    const form = this.element.closest('form') || this.element.querySelector('form')
    if (form) {
      form.addEventListener("submit", (event) => {
        console.log("Form submitting - updating hidden fields")
        console.log("Selected items:", this.selectedItems)
        console.log("Is initialized:", this.isInitialized)
        
        // Always update hidden fields before submission
        this.updateHiddenField()
        
        // Small delay to ensure DOM updates complete
        // Note: This is synchronous, so fields should be in DOM already
        const hiddenFields = form.querySelectorAll('input[name="outfit[inventory_item_ids][]"]')
        console.log(`Form submit: Found ${hiddenFields.length} hidden fields`)
        hiddenFields.forEach((field, idx) => {
          console.log(`  Submit field ${idx}: value="${field.value}"`)
        })
        
        // Verify fields are present - if not, prevent submission
        if (hiddenFields.length === 0 && this.selectedItems.length > 0) {
          console.error("ERROR: Selected items exist but no hidden fields found!")
          console.error("This indicates a bug in updateHiddenField()")
        }
      }, { capture: true }) // Use capture phase to run before default submission
    }
  }

  initializeExistingItems() {
    // Find all hidden fields with existing item IDs (only those marked as existing)
    const hiddenFields = this.element.querySelectorAll('input[name="outfit[inventory_item_ids][]"].existing-outfit-item')
    const existingItemIds = []
    
    hiddenFields.forEach(field => {
      const value = field.value.trim()
      if (value && value !== '') {
        const id = parseInt(value)
        if (!isNaN(id)) {
          existingItemIds.push(id)
        }
      }
    })

    if (existingItemIds.length > 0) {
      // We'll populate these after fetching inventory items
      this.pendingItemIds = existingItemIds
      console.log("Found existing outfit items:", existingItemIds)
    }
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
        // Debug: Log first item to verify image structure
        if (this.inventoryItems.length > 0) {
          console.log("Sample inventory item:", this.inventoryItems[0])
          console.log("Image structure:", this.inventoryItems[0]?.images)
        }
        
        // Load existing outfit items if we're editing
        if (this.pendingItemIds && this.pendingItemIds.length > 0) {
          this.loadExistingItems(this.pendingItemIds)
          delete this.pendingItemIds
        }
        
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

    // SVG placeholder as data URI (clothing icon)
    const placeholderImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23e5e7eb'/%3E%3Cg fill='%239ca3af'%3E%3Cpath d='M60 70h80v80H60z'/%3E%3Ccircle cx='100' cy='95' r='12'/%3E%3Cpath d='M70 135l30-25 20 15 20-20 30 30H70z'/%3E%3C/g%3E%3C/svg%3E"
    
    this.itemsGridTarget.innerHTML = this.inventoryItems.map(item => {
      // Try to get image URL with proper fallback chain
      let imageUrl = placeholderImage
      if (item.images?.primary?.urls) {
        imageUrl = item.images.primary.urls.thumb || item.images.primary.urls.medium || item.images.primary.urls.original || placeholderImage
      }
      
      // Debug: Log if image URL is missing
      if (!item.images?.primary?.urls) {
        console.warn(`Item ${item.id} (${item.name}) has no image URLs:`, item.images)
      }
      
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
      
      const categoryName = item.category?.name || 'Uncategorized'
      const escapedImageUrl = escapeHtml(imageUrl)
      const escapedPlaceholder = escapeHtml(placeholderImage)
      const escapedItemName = escapeHtml(item.name)
      const escapedCategoryName = escapeHtml(categoryName)
      const jsEscapedPlaceholder = escapeJs(placeholderImage)
      
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

    // Reset drag state
    document.querySelectorAll('[draggable="true"]').forEach(el => {
      el.style.opacity = "1"
    })
  }

  handleItemClick(event) {
    // Prevent adding item if clicking on remove button
    if (event.target.closest('button')) {
      return
    }
    
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
    // Normalize IDs for comparison (handle both string and number)
    const normalizeId = (id) => parseInt(id)
    const itemId = normalizeId(itemData.id)
    
    // Check if item already exists
    if (this.selectedItems.find(item => normalizeId(item.id) === itemId)) {
      return
    }

    this.selectedItems.push(itemData)
    this.renderSelectedItems()
    this.updateHiddenField()
    // Removed: updateCompletenessScore and updateColorAnalysis (progress bars removed)
    this.requestAiSuggestions()
  }

  removeItem(itemId) {
    // Normalize IDs for comparison (handle both string and number)
    const normalizeId = (id) => parseInt(id)
    const id = normalizeId(itemId)
    
    this.selectedItems = this.selectedItems.filter(item => {
      return normalizeId(item.id) !== id
    })
    this.renderSelectedItems()
    this.updateHiddenField()
    // Removed: updateCompletenessScore and updateColorAnalysis (progress bars removed)
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

    this.selectedItemsTarget.innerHTML = this.selectedItems.map((item, index) => {
      const imageUrl = item.image_url || placeholderImage
      const escapedImageUrl = escapeHtml(imageUrl)
      const escapedPlaceholder = escapeHtml(placeholderImage)
      const jsEscapedPlaceholder = escapeJs(placeholderImage)
      const escapedItemName = escapeHtml(item.name)
      const escapedCategory = escapeHtml(item.category)
      
      return `
      <div class="relative group border rounded-lg p-3 bg-white dark:bg-gray-800" data-item-id="${item.id}">
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
          class="w-full h-24 object-cover rounded mb-2 bg-gray-100 dark:bg-gray-700"
          onerror="this.src='${jsEscapedPlaceholder}'"
        />
        <div class="text-sm font-medium text-gray-900 dark:text-white truncate">${escapedItemName}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">${escapedCategory}</div>
      </div>
    `
    }).join('')
  }

  // Removed: All progress bar related methods (updateCompletenessScore, calculateCompletenessScore, getCompletenessMessage, updateColorAnalysis, renderColorAnalysis)

  loadExistingItems(itemIds) {
    // Find items from inventoryItems array and add to selectedItems
    itemIds.forEach(itemId => {
      const item = this.inventoryItems.find(inv => parseInt(inv.id) === parseInt(itemId))
      if (item) {
        // Convert API format to our format
        const itemData = {
          id: item.id,
          name: item.name || 'Unnamed Item',
          category: item.category?.name || 'Uncategorized',
          image_url: item.images?.primary?.urls?.thumb || 
                     item.images?.primary?.urls?.medium || 
                     item.images?.primary?.urls?.original || 
                     null
        }
        // Check if already added (avoid duplicates)
        if (!this.selectedItems.find(sel => parseInt(sel.id) === parseInt(itemData.id))) {
          this.selectedItems.push(itemData)
        }
      }
    })
    
    // If some items weren't found in the current fetch, try to fetch them individually
    const missingIds = itemIds.filter(id => !this.inventoryItems.find(inv => parseInt(inv.id) === parseInt(id)))
    if (missingIds.length > 0) {
      this.fetchMissingItems(missingIds)
    } else {
      // All items loaded, render the canvas and update hidden fields
      this.renderSelectedItems()
      // CRITICAL: Update hidden fields immediately after loading existing items
      this.updateHiddenField()
    }
  }

  async fetchMissingItems(itemIds) {
    // Fetch specific items that weren't in the main fetch
    try {
      const promises = itemIds.map(async (id) => {
        try {
          const response = await fetch(`/api/v1/inventory_items/${id}`, {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              "Accept": "application/json",
              "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')?.content || ""
            },
            credentials: "include"
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
      // CRITICAL: Update hidden fields after fetching missing items
      this.updateHiddenField()
    } catch (error) {
      console.error("Error fetching missing items:", error)
      this.renderSelectedItems() // Render what we have
      // Still update hidden fields with what we have
      this.updateHiddenField()
    }
  }

  updateHiddenField() {
    // Find the form element - it's inside the controller element (child), not an ancestor
    // Try closest first (in case form is parent), then querySelector (if form is child)
    const form = this.element.closest('form') || this.element.querySelector('form')
    if (!form) {
      console.error("Could not find form element")
      return
    }

    // Count existing fields before removal (for safety check)
    const existingFieldsBefore = Array.from(form.querySelectorAll('input[name="outfit[inventory_item_ids][]"].existing-outfit-item'))
    const existingFieldCount = existingFieldsBefore.length
    const existingFieldValues = existingFieldsBefore.map(field => field.value).filter(v => v && v.trim() !== '')
    
    // Remove all existing hidden fields for inventory_item_ids
    // This includes both existing-outfit-item fields and dynamically added ones
    form.querySelectorAll('input[name="outfit[inventory_item_ids][]"]').forEach(el => el.remove())
    
    // Debug: Log selected items
    console.log("Updating hidden fields for selected items:", this.selectedItems)
    console.log("Selected items count:", this.selectedItems.length)
    console.log("Existing fields before removal:", existingFieldCount)
    console.log("Existing field values:", existingFieldValues)
    console.log("Is initialized:", this.isInitialized)
    
    // SAFEGUARD: If selectedItems is empty but we're on edit page with existing fields and not initialized,
    // this means initialization hasn't completed. Preserve the existing fields.
    if (this.selectedItems.length === 0 && existingFieldValues.length > 0 && !this.isInitialized) {
      console.warn("WARNING: selectedItems is empty but existing fields found and not initialized yet.")
      console.warn("This should not happen if initialization is working correctly.")
      console.warn("Re-adding existing fields as fallback...")
      
      // Re-add existing fields as fallback
      existingFieldValues.forEach(value => {
        const input = document.createElement('input')
        input.type = 'hidden'
        input.name = 'outfit[inventory_item_ids][]'
        input.value = value
        form.appendChild(input)
        console.log("Re-added existing field:", input.name, "=", input.value)
      })
      return
    }
    
    // Add new hidden fields for each selected item
    // CRITICAL: If selectedItems is empty, we remove all fields (this is intentional for clearing)
    // But we should ensure selectedItems is properly populated before form submission
    this.selectedItems.forEach((item, index) => {
      const input = document.createElement('input')
      input.type = 'hidden'
      input.name = 'outfit[inventory_item_ids][]'
      input.value = String(item.id) // Ensure it's a string
      
      // Append directly to the form to ensure it's submitted
      form.appendChild(input)
      
      console.log(`Added hidden field ${index + 1}:`, input.name, "=", input.value, "for item:", item.name)
    })
    
    // Verify fields were added
    const allHiddenFields = form.querySelectorAll('input[name="outfit[inventory_item_ids][]"]')
    console.log(`Total hidden fields after update: ${allHiddenFields.length}`)
    if (allHiddenFields.length > 0) {
      allHiddenFields.forEach((field, index) => {
        console.log(`  Field ${index}: value="${field.value}"`)
      })
    } else {
      console.warn("WARNING: No hidden fields were added! This means selectedItems is empty.")
      console.warn("This is OK if user intentionally cleared all items, but may be a bug otherwise.")
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

  handleRemoveItem(event) {
    event.preventDefault()
    event.stopPropagation()
    const itemId = event.currentTarget.dataset.itemId || event.currentTarget.closest('[data-item-id]')?.dataset.itemId
    if (itemId) {
      this.removeItem(parseInt(itemId))
    }
  }

  // Removed: updateColorAnalysis and renderColorAnalysis methods (progress bars removed)
}
