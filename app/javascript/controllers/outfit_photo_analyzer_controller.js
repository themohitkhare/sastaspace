import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="outfit-photo-analyzer"
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
    "analysisProgress",
    "reviewStep",
    "itemsGrid",
    "createButton",
    "outfitStep",
    "createdItemsInfo",
    "builderLink"
  ]

  connect() {
    this.jobId = null
    this.blobId = null
    this.detectedItems = []
    this.createdItemIds = []
    this.pollInterval = null
    this.maxPollAttempts = 30 // 30 attempts * 3 seconds = 90 seconds max
    this.pollAttempts = 0
  }

  disconnect() {
    this.stopPolling()
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

    if (file.size > 5 * 1024 * 1024) {
      this.showError("Image must be less than 5MB")
      return
    }

    // Show preview
    this.showPreview(file)

    // Hide upload prompt and error state
    this.uploadPromptTarget.classList.add("hidden")
    this.hideError()

    // Show loading state
    this.showLoading()

    // Upload and start analysis
    try {
      await this.uploadAndAnalyze(file)
    } catch (error) {
      console.error("Error uploading file:", error)
      this.showError("Failed to upload image. Please try again.")
      this.hideLoading()
    }
  }

  async uploadAndAnalyze(file) {
    const formData = new FormData()
    formData.append("image", file)

    const response = await fetch("/api/v1/outfits/analyze_photo", {
      method: "POST",
      headers: {
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      },
      credentials: "include",
      body: formData
    })

    const data = await response.json()

    if (!response.ok || !data.success) {
      throw new Error(data.error?.message || "Failed to start analysis")
    }

    // Store job ID and blob ID
    this.jobId = data.data.job_id
    this.blobId = data.data.blob_id
    
    console.log("Outfit photo uploaded. Received blobId:", this.blobId, "jobId:", this.jobId)
    
    this.startPolling()
  }

  startPolling() {
    this.pollAttempts = 0
    this.pollInterval = setInterval(() => {
      this.checkStatus()
    }, 3000) // Poll every 3 seconds

    // Also check immediately
    this.checkStatus()
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval)
      this.pollInterval = null
    }
  }

  async checkStatus() {
    if (!this.jobId) return

    this.pollAttempts++

    try {
      const response = await fetch(`/api/v1/outfits/analyze_photo_status/${this.jobId}`, {
        method: "GET",
        headers: {
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include"
      })

      const data = await response.json()

      if (!response.ok && data.error) {
        throw new Error(data.error.message || "Failed to check status")
      }

      const status = data.data?.status

      if (status === "completed") {
        this.stopPolling()
        this.handleAnalysisComplete(data.data.analysis)
      } else if (status === "failed") {
        this.stopPolling()
        this.showError(data.data?.error?.message || data.data?.error?.error || "Analysis failed. Please try again.")
        this.hideLoading()
      } else if (status === "processing") {
        // Update progress message
        if (this.hasAnalysisProgressTarget) {
          this.analysisProgressTarget.textContent = `Analyzing... (attempt ${this.pollAttempts}/${this.maxPollAttempts})`
        }
        
        if (this.pollAttempts >= this.maxPollAttempts) {
          this.stopPolling()
          this.showError("Analysis is taking longer than expected. Please try again.")
          this.hideLoading()
        }
      }
      // Continue polling if still processing
    } catch (error) {
      console.error("Error checking status:", error)
      if (this.pollAttempts >= this.maxPollAttempts) {
        this.stopPolling()
        this.showError("Failed to check analysis status. Please try again.")
        this.hideLoading()
      }
    }
  }

  handleAnalysisComplete(analysis) {
    this.hideLoading()

    // Store detected items
    this.detectedItems = analysis.items || []
    
    if (this.detectedItems.length === 0) {
      this.showError("No items were detected in the outfit photo. Please try a different photo.")
      return
    }

    // Show review step
    this.showReviewStep()
    this.renderItemsGrid()
  }

  showReviewStep() {
    this.uploadStepTarget.classList.add("hidden")
    this.reviewStepTarget.classList.remove("hidden")
  }

  renderItemsGrid() {
    this.itemsGridTarget.innerHTML = ""

    this.detectedItems.forEach((item, index) => {
      const itemCard = this.createItemCard(item, index)
      this.itemsGridTarget.appendChild(itemCard)
    })
  }

  createItemCard(item, index) {
    const card = document.createElement("div")
    card.className = "border rounded-lg p-4 bg-white dark:bg-gray-800"
    card.dataset.index = index

    const categoryName = item.category_matched || item.category_name || "Unknown"
    const confidence = (item.confidence || 0) * 100

    card.innerHTML = `
      <div class="space-y-3">
        <div class="flex items-start justify-between">
          <h3 class="font-semibold text-gray-900 dark:text-white">${this.escapeHtml(item.name || "Unnamed Item")}</h3>
          <span class="text-xs text-gray-500 dark:text-gray-400">${confidence.toFixed(0)}%</span>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Category</label>
          <input 
            type="text" 
            value="${this.escapeHtml(categoryName)}" 
            data-outfit-photo-analyzer-item-index="${index}"
            data-outfit-photo-analyzer-item-field="category_name"
            class="form-input text-sm w-full"
            readonly
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
          <textarea 
            rows="3"
            data-outfit-photo-analyzer-item-index="${index}"
            data-outfit-photo-analyzer-item-field="description"
            class="form-input text-sm w-full"
          >${this.escapeHtml(item.description || "")}</textarea>
        </div>
        
        ${item.brand_matched || item.brand_name ? `
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Brand</label>
            <input 
              type="text" 
              value="${this.escapeHtml(item.brand_matched || item.brand_name || "")}" 
              data-outfit-photo-analyzer-item-index="${index}"
              data-outfit-photo-analyzer-item-field="brand_name"
              class="form-input text-sm w-full"
              readonly
            />
          </div>
        ` : ""}
        
        <div class="text-xs text-gray-500 dark:text-gray-400">
          Position: ${item.position || "unknown"}
        </div>
      </div>
    `

    // Add event listeners for editable fields
    const inputs = card.querySelectorAll('[data-outfit-photo-analyzer-item-field]')
    inputs.forEach(input => {
      input.addEventListener('change', () => {
        this.updateItemData(index, input.dataset.outfitPhotoAnalyzerItemField, input.value)
      })
    })

    return card
  }

  updateItemData(index, field, value) {
    if (this.detectedItems[index]) {
      this.detectedItems[index][field] = value
    }
  }

  cancelReview() {
    // Reset and show upload step
    this.reviewStepTarget.classList.add("hidden")
    this.uploadStepTarget.classList.remove("hidden")
    this.detectedItems = []
    this.blobId = null
    this.jobId = null
  }

  async createItems() {
    if (!this.detectedItems || this.detectedItems.length === 0) {
      this.showError("No items to create")
      return
    }

    // Disable create button
    this.createButtonTarget.disabled = true
    this.createButtonTarget.textContent = "Creating items..."

    try {
      // Prepare items for batch creation
      const itemsData = this.detectedItems.map(item => ({
        name: item.name || "Unnamed Item",
        description: item.description || "",
        category_id: item.category_id,
        brand_id: item.brand_id,
        // Note: For now, all items share the same blob_id (outfit photo)
        // Future improvement: crop individual items from the photo
        blob_id: this.blobId,
        status: "active"
      }))

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

      // Store created item IDs
      this.createdItemIds = data.data.inventory_items.map(item => item.id)

      // Show outfit creation step
      this.showOutfitStep(data.data.inventory_items)
    } catch (error) {
      console.error("Error creating items:", error)
      this.showError("Failed to create items. Please try again.")
      this.createButtonTarget.disabled = false
      this.createButtonTarget.textContent = "Create Items"
    }
  }

  showOutfitStep(createdItems) {
    this.reviewStepTarget.classList.add("hidden")
    this.outfitStepTarget.classList.remove("hidden")

    // Update builder link with item IDs
    const itemIdsParam = this.createdItemIds.join(",")
    if (this.builderLinkTarget) {
      const currentHref = this.builderLinkTarget.getAttribute("href")
      this.builderLinkTarget.setAttribute("href", `${currentHref}?items=${itemIdsParam}`)
    }

    // Show created items info
    this.createdItemsInfoTarget.innerHTML = `
      <h3 class="font-semibold text-green-900 dark:text-green-200 mb-2">
        ✓ Successfully created ${createdItems.length} item(s)
      </h3>
      <ul class="list-disc list-inside text-sm text-green-800 dark:text-green-300 space-y-1">
        ${createdItems.map(item => `<li>${this.escapeHtml(item.name)}</li>`).join("")}
      </ul>
      <p class="mt-3 text-sm text-green-700 dark:text-green-400">
        You can now create an outfit with these items using the outfit builder.
      </p>
    `
  }

  retryAnalysis() {
    this.hideError()
    this.uploadPromptTarget.classList.remove("hidden")
    this.imagePreviewTarget.classList.add("hidden")
    this.detectedItems = []
    this.createdItemIds = []
    this.blobId = null
    this.jobId = null
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
    if (this.hasAnalysisProgressTarget) {
      this.analysisProgressTarget.textContent = "Starting analysis..."
    }
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
    const div = document.createElement("div")
    div.textContent = text
    return div.innerHTML
  }
}

