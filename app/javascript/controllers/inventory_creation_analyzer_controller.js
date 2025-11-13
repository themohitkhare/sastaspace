import { Controller } from "@hotwired/stimulus"
import { createConsumer } from "@rails/actioncable"

// Connects to data-controller="inventory-creation-analyzer"
// Updated to use clothing detection for multi-item detection with WebSocket updates
export default class extends Controller {
  static targets = [
    "uploadArea",
    "uploadStep",
    "fileInput",
    "uploadPrompt",
    "imagePreview",
    "previewImage",
    "previewName",
    "loadingState",
    "errorState",
    "errorMessage",
    "reviewStep",
    "itemsGrid",
    "createButton",
    "selectedItemsCount",
    "successStep",
    "successMessage"
  ]

  connect() {
    this.blobId = null
    this.analysisId = null
    this.detectedItems = []
    this.selectedItems = []
    this.cable = null
    this.detectionSubscription = null
    this.jobId = null
    this.userId = null
  }

  disconnect() {
    this.unsubscribe()
  }

  unsubscribe() {
    if (this.detectionSubscription) {
      this.detectionSubscription.unsubscribe()
      this.detectionSubscription = null
    }

    if (this.cable) {
      this.cable.disconnect()
      this.cable = null
    }
  }

  triggerFileInput() {
    this.fileInputTarget.click()
  }

  handleFileSelect(event) {
    const file = event.target.files[0]
    if (file) {
      this.handleFile(file)
    }
  }

  handleDragOver(event) {
    event.preventDefault()
    event.stopPropagation()
    this.uploadAreaTarget.classList.add("border-primary-500")
  }

  handleDrop(event) {
    event.preventDefault()
    event.stopPropagation()
    this.uploadAreaTarget.classList.remove("border-primary-500")
    
    const file = event.dataTransfer.files[0]
    if (file && file.type.startsWith("image/")) {
      this.handleFile(file)
    } else {
      this.showError("Please upload an image file")
    }
  }

  async handleFile(file) {
    // Validate file
    if (!file.type.match(/^image\/(jpeg|jpg|png|webp)$/)) {
      this.showError("Please upload a JPEG, PNG, or WebP image")
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      this.showError("Image must be less than 10MB")
      return
    }

    // Show preview
    this.showPreview(file)

    // Hide upload prompt and error state
    this.uploadPromptTarget.classList.add("hidden")
    this.hideError()

    // Upload and queue job (no loading state - show queued immediately)
    try {
      await this.uploadAndAnalyze(file)
    } catch (error) {
      console.error("Error uploading file:", error)
      const errorMessage = error.message || "Failed to queue image processing. Please try again."
      this.showError(errorMessage)
      // Reset preview on error
      if (this.hasImagePreviewTarget) {
        this.imagePreviewTarget.classList.add("hidden")
      }
      if (this.hasUploadPromptTarget) {
        this.uploadPromptTarget.classList.remove("hidden")
      }
    }
  }

  async uploadAndAnalyze(file) {
    const formData = new FormData()
    formData.append("image", file)

    const response = await fetch("/api/v1/clothing_detection/analyze", {
      method: "POST",
      headers: {
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      },
      credentials: "include",
      body: formData
    })

    const data = await response.json()

    if (!response.ok || !data.success) {
      console.error("API Error Response:", {
        status: response.status,
        statusText: response.statusText,
        data: data
      })
      throw new Error(data.error?.message || data.error?.code || "Failed to analyze image")
    }

    // Store job and user info
    this.blobId = data.data.blob_id
    this.jobId = data.data.job_id
    this.userId = data.data.user_id

    console.log("Clothing detection job queued. Job ID:", this.jobId)
    console.log("Full API response:", JSON.stringify(data, null, 2))

    // Store job info in sessionStorage for inventory page (if user navigates there)
    if (this.jobId && this.userId) {
      sessionStorage.setItem('pending_detection_job', JSON.stringify({
        job_id: this.jobId,
        user_id: this.userId,
        blob_id: this.blobId,
        timestamp: Date.now()
      }))
    }

    // Hide loading state immediately - don't make user wait
    this.hideLoading()

    // Show success state immediately with "queued" message
    this.showQueuedState()

    // Set up WebSocket subscription to update message when complete (optional, non-blocking)
    if (this.userId) {
      this.setupWebSocketSubscription()
    }
  }

  setupWebSocketSubscription() {
    if (!this.userId) {
      console.error("Cannot set up WebSocket: user_id is missing")
      return
    }

    // Create ActionCable consumer
    this.cable = createConsumer()

    // Subscribe to detection updates
    this.detectionSubscription = this.cable.subscriptions.create(
      {
        channel: "AiProcessingChannel",
        user_id: this.userId.toString()
      },
      {
        received: (data) => this.handleDetectionUpdate(data),
        connected: () => {
          console.log("Connected to detection channel for user", this.userId)
        },
        disconnected: () => {
          console.log("Disconnected from detection channel")
        }
      }
    )
  }

  handleDetectionUpdate(data) {
    console.log("Detection update received:", data)

    switch (data.type) {
      case "progress_update":
        this.updateProgressMessage(data.message)
        break

      case "detection_complete":
        this.handleDetectionComplete(data)
        break

      case "detection_error":
        this.handleDetectionError(data.error)
        break

      default:
        console.warn("Unknown detection update type:", data.type)
    }
  }

  updateProgressMessage(message) {
    // Update loading message if we have a progress target
    if (this.hasLoadingStateTarget) {
      const loadingText = this.loadingStateTarget.querySelector('p')
      if (loadingText) {
        loadingText.textContent = message
      }
    }
  }

  handleDetectionComplete(data) {
    console.log("Detection completed:", data.items_detected, "items found,", data.created_items_count || 0, "items created")

    // Unsubscribe from WebSocket
    this.unsubscribe()

    // Hide loading state
    this.hideLoading()

    // Show success state
    this.showSuccessState(data.created_items_count || data.items_detected || 0)
  }

  handleDetectionError(error) {
    console.error("Detection error:", error)

    // Unsubscribe from WebSocket
    this.unsubscribe()

    // Hide loading and show error
    this.hideLoading()
    this.showError(error || "Failed to detect clothing items. Please try again.")
  }

  showQueuedState() {
    // Hide upload step
    if (this.hasUploadStepTarget) {
      this.uploadStepTarget.classList.add("hidden")
    }

    // Hide review step if visible
    if (this.hasReviewStepTarget) {
      this.reviewStepTarget.classList.add("hidden")
    }

    // Show success step
    if (this.hasSuccessStepTarget) {
      this.successStepTarget.classList.remove("hidden")
    }

    // Show queued message
    if (this.hasSuccessMessageTarget) {
      this.successMessageTarget.textContent = "Your image has been queued for processing. Items will be added to your inventory automatically when detection completes."
    }
  }

  showSuccessState(itemsCount) {
    // Hide upload step
    if (this.hasUploadStepTarget) {
      this.uploadStepTarget.classList.add("hidden")
    }

    // Hide review step if visible
    if (this.hasReviewStepTarget) {
      this.reviewStepTarget.classList.add("hidden")
    }

    // Show success step
    if (this.hasSuccessStepTarget) {
      this.successStepTarget.classList.remove("hidden")
    }

    // Update success message with actual count
    if (this.hasSuccessMessageTarget) {
      const itemText = itemsCount === 1 ? "item" : "items"
      this.successMessageTarget.textContent = `Successfully created ${itemsCount} ${itemText} in your inventory!`
    }
  }

  addMore() {
    // Reset form and show upload step again
    if (this.hasSuccessStepTarget) {
      this.successStepTarget.classList.add("hidden")
    }

    if (this.hasUploadStepTarget) {
      this.uploadStepTarget.classList.remove("hidden")
    }

    // Reset state
    this.blobId = null
    this.analysisId = null
    this.detectedItems = []
    this.selectedItems = []
    this.jobId = null
    this.userId = null

    // Reset file input
    if (this.hasFileInputTarget) {
      this.fileInputTarget.value = ""
    }

    // Reset preview
    if (this.hasImagePreviewTarget) {
      this.imagePreviewTarget.classList.add("hidden")
    }

    if (this.hasUploadPromptTarget) {
      this.uploadPromptTarget.classList.remove("hidden")
    }

    // Hide any error states
    this.hideError()
  }


  showReviewStep() {
    // Hide upload step
    this.uploadStepTarget.classList.add("hidden")
    
    // Show review step
    this.reviewStepTarget.classList.remove("hidden")
    
    // Render detected items
    this.renderDetectedItems()
  }

  renderDetectedItems() {
    if (!this.hasItemsGridTarget) return

    this.itemsGridTarget.innerHTML = ""

    if (!this.detectedItems || this.detectedItems.length === 0) {
      console.warn("No items detected. detectedItems:", this.detectedItems)
      this.itemsGridTarget.innerHTML = `
        <div class="col-span-full text-center py-8 text-gray-500">
          <p>No items detected in this image.</p>
          <p class="text-sm mt-2">This could be because:</p>
          <ul class="text-sm mt-2 list-disc list-inside">
            <li>The image doesn't contain visible clothing items</li>
            <li>Items detected don't match your gender preference</li>
            <li>The image quality is too low</li>
          </ul>
          <button
            type="button"
            data-action="click->inventory-creation-analyzer#cancelReview"
            class="mt-4 text-primary-600 hover:text-primary-700 underline"
          >
            Try a different image
          </button>
        </div>
      `
      return
    }

    // Select all items by default
    this.selectedItems = this.detectedItems.map((item, index) => index)

    this.detectedItems.forEach((item, index) => {
      const itemCard = this.createItemCard(item, index)
      this.itemsGridTarget.appendChild(itemCard)
    })

    this.updateSelectedCount()
  }

  createItemCard(item, index) {
    const card = document.createElement("div")
    card.className = "border rounded-lg p-4 bg-white dark:bg-gray-800"
    card.dataset.itemIndex = index

    const isSelected = this.selectedItems.includes(index)
    const genderBadge = this.getGenderBadge(item.gender_styling)
    const priorityBadge = this.getPriorityBadge(item.extraction_priority)
    const confidencePercent = Math.round((item.confidence || 0.5) * 100)

    card.innerHTML = `
      <div class="flex items-start gap-3">
        <input
          type="checkbox"
          ${isSelected ? "checked" : ""}
          data-action="change->inventory-creation-analyzer#toggleItem"
          data-item-index="${index}"
          class="mt-1 h-4 w-4 text-primary-600 rounded border-gray-300"
        />
        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-2 mb-2">
            <div class="flex-1">
              <h3 class="font-semibold text-gray-900 dark:text-white">${this.escapeHtml(item.item_name || "Unnamed Item")}</h3>
              <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">${this.escapeHtml(item.category || "")} ${item.subcategory ? `• ${this.escapeHtml(item.subcategory)}` : ""}</p>
            </div>
            <div class="flex gap-2 flex-shrink-0">
              ${genderBadge}
              ${priorityBadge}
            </div>
          </div>
          
          <div class="space-y-1 text-sm text-gray-600 dark:text-gray-400">
            ${item.color_primary ? `<p><span class="font-medium">Color:</span> ${this.escapeHtml(item.color_primary)}${item.color_secondary ? `, ${this.escapeHtml(item.color_secondary)}` : ""}</p>` : ""}
            ${item.material_type ? `<p><span class="font-medium">Material:</span> ${this.escapeHtml(item.material_type)}</p>` : ""}
            ${item.style_category ? `<p><span class="font-medium">Style:</span> ${this.escapeHtml(item.style_category)}</p>` : ""}
            ${item.pattern_type && item.pattern_type !== "solid" ? `<p><span class="font-medium">Pattern:</span> ${this.escapeHtml(item.pattern_details || item.pattern_type)}</p>` : ""}
          </div>
          
          <div class="mt-2 flex items-center gap-2 text-xs text-gray-500">
            <span>Confidence: ${confidencePercent}%</span>
          </div>
        </div>
      </div>
    `

    return card
  }

  getGenderBadge(gender) {
    const badges = {
      men: '<span class="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">Men\'s</span>',
      women: '<span class="px-2 py-1 text-xs rounded bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200">Women\'s</span>',
      unisex: '<span class="px-2 py-1 text-xs rounded bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">Unisex</span>'
    }
    return badges[gender] || badges.unisex
  }

  getPriorityBadge(priority) {
    const badges = {
      high: '<span class="px-2 py-1 text-xs rounded bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">High Priority</span>',
      medium: '<span class="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">Medium</span>',
      low: '<span class="px-2 py-1 text-xs rounded bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Low</span>'
    }
    return badges[priority] || badges.medium
  }

  toggleItem(event) {
    const index = parseInt(event.target.dataset.itemIndex)
    if (event.target.checked) {
      if (!this.selectedItems.includes(index)) {
        this.selectedItems.push(index)
      }
    } else {
      this.selectedItems = this.selectedItems.filter(i => i !== index)
    }
    this.updateSelectedCount()
  }

  updateSelectedCount() {
    if (this.hasSelectedItemsCountTarget) {
      const count = this.selectedItems.length
      this.selectedItemsCountTarget.textContent = `${count} item${count !== 1 ? "s" : ""} selected`
    }

    if (this.hasCreateButtonTarget) {
      this.createButtonTarget.disabled = this.selectedItems.length === 0
    }
  }

  async createItems() {
    if (this.selectedItems.length === 0) {
      this.showError("Please select at least one item to create")
      return
    }

    // Disable create button
    if (this.hasCreateButtonTarget) {
      this.createButtonTarget.disabled = true
      this.createButtonTarget.textContent = "Creating items..."
    }

    try {
      // Prepare items for batch creation
      const itemsData = this.selectedItems.map(index => {
        const item = this.detectedItems[index]
        
        return {
          name: item.item_name || "Unnamed Item",
          description: this.buildDescription(item),
          category_id: item.category_id, // Already matched by ClothingDetectionService
          blob_id: this.blobId,
          status: "active",
          metadata: {
            color: item.color_primary,
            material: item.material_type,
            style_category: item.style_category,
            gender_styling: item.gender_styling,
            pattern_type: item.pattern_type,
            pattern_details: item.pattern_details
          }
        }
      })

      const response = await fetch("/api/v1/inventory_items/batch_create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include",
        body: JSON.stringify({ items: itemsData })
      })

      const data = await response.json()

      if (!response.ok || !data.success) {
        throw new Error(data.error?.message || "Failed to create items")
      }

      // Redirect to inventory items page
      window.location.href = "/inventory_items"
    } catch (error) {
      console.error("Error creating items:", error)
      this.showError("Failed to create items. Please try again.")
      if (this.hasCreateButtonTarget) {
        this.createButtonTarget.disabled = false
        this.createButtonTarget.textContent = "Create Selected Items"
      }
    }
  }

  buildDescription(item) {
    const parts = []
    if (item.color_primary) parts.push(item.color_primary)
    if (item.color_secondary) parts.push(item.color_secondary)
    if (item.material_type) parts.push(item.material_type)
    if (item.style_category) parts.push(item.style_category)
    if (item.pattern_details) parts.push(item.pattern_details)
    
    return parts.join(", ") || item.item_name || "No description available"
  }

  cancelReview() {
    this.reviewStepTarget.classList.add("hidden")
    this.uploadStepTarget.classList.remove("hidden")
    this.imagePreviewTarget.classList.add("hidden")
    this.uploadPromptTarget.classList.remove("hidden")
    this.fileInputTarget.value = ""
    this.detectedItems = []
    this.selectedItems = []
    this.blobId = null
    this.analysisId = null
  }

  showPreview(file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      this.previewImageTarget.src = e.target.result
      this.previewNameTarget.textContent = file.name
      this.imagePreviewTarget.classList.remove("hidden")
    }
    reader.readAsDataURL(file)
  }

  showLoading() {
    this.loadingStateTarget.classList.remove("hidden")
    this.hideError()
  }

  hideLoading() {
    this.loadingStateTarget.classList.add("hidden")
  }

  showError(message) {
    this.errorMessageTarget.textContent = message
    this.errorStateTarget.classList.remove("hidden")
    this.hideLoading()
  }

  hideError() {
    this.errorStateTarget.classList.add("hidden")
  }

  escapeHtml(text) {
    if (!text) return ""
    const div = document.createElement("div")
    div.textContent = text
    return div.innerHTML
  }
}
