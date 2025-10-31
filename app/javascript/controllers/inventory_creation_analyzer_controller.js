import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="inventory-creation-analyzer"
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
    "successMessage",
    "nextButton",
    // Form fields
    "categoryField",
    "nameField",
    "descriptionField"
  ]

  connect() {
    this.jobId = null
    this.blobId = null // Store the blob ID for the uploaded image
    this.pollInterval = null
    this.maxPollAttempts = 20 // 20 attempts * 3 seconds = 60 seconds max
    this.pollAttempts = 0

    // Ensure blob_id is attached when form is submitted (before it's sent)
    const form = this.element.closest("form")
    if (form) {
      form.addEventListener("submit", (e) => {
        // Attach blob_id right before submission
        this.attachPrimaryImage()
        // Don't prevent default - let form submit normally
      }, { capture: true }) // Use capture phase to ensure it runs first
    }
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

    const response = await fetch("/api/v1/inventory_items/analyze_image_for_creation", {
      method: "POST",
      headers: {
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      },
      credentials: "include", // Include cookies for authentication
      body: formData
    })

    const data = await response.json()

    if (!response.ok || !data.success) {
      throw new Error(data.error?.message || "Failed to start analysis")
    }

    // Store job ID and blob ID, then start polling
    this.jobId = data.data.job_id
    this.blobId = data.data.blob_id // Store blob ID for later attachment
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
      const response = await fetch(`/api/v1/inventory_items/analyze_image_status/${this.jobId}`, {
        method: "GET",
        headers: {
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include" // Include cookies for authentication
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
        this.showError(data.data?.error?.message || "Analysis failed. Please try again.")
        this.hideLoading()
      } else if (this.pollAttempts >= this.maxPollAttempts) {
        this.stopPolling()
        this.showError("Analysis is taking longer than expected. Please try again or fill the form manually.")
        this.hideLoading()
      }
      // If still processing, continue polling
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
    this.showSuccess()

    // Store blob ID from analysis if available (fallback from job status)
    if (analysis.blob_id) {
      this.blobId = analysis.blob_id
    }

    // Fill form fields with analysis data
    this.fillForm(analysis)

    // Attach the blob_id to the form immediately (it will be included in submit)
    this.attachPrimaryImage()

    // Move to next step after a brief delay
    setTimeout(() => {
      this.moveToNextStep()
    }, 1000)
  }

  attachPrimaryImage() {
    if (!this.blobId) {
      console.warn("No blobId available to attach to form")
      return
    }

    // Create a hidden input with the blob ID that Rails can use
    const form = this.element.closest("form")
    if (!form) {
      console.warn("No form found to attach blob_id")
      return
    }

    // Remove any existing blob_id input to avoid duplicates
    const existingInput = form.querySelector('input[name="inventory_item[blob_id]"]')
    if (existingInput) {
      existingInput.remove()
    }

    // Create new hidden input with blob_id
    const hiddenInput = document.createElement("input")
    hiddenInput.type = "hidden"
    hiddenInput.name = "inventory_item[blob_id]"
    hiddenInput.value = this.blobId
    form.appendChild(hiddenInput)
    
    console.log("Attached blob_id to form:", this.blobId, "Form action:", form.action)
    
    // Verify it was added
    const verify = form.querySelector('input[name="inventory_item[blob_id]"]')
    if (verify) {
      console.log("Verified blob_id input exists with value:", verify.value)
    } else {
      console.error("Failed to add blob_id input to form!")
    }
  }

  fillForm(analysis) {
    // Fill category
    if (analysis.category_id && this.hasCategoryFieldTarget) {
      this.categoryFieldTarget.value = analysis.category_id
      this.categoryFieldTarget.dispatchEvent(new Event("change", { bubbles: true }))
      
      // Update the category picker display if it exists
      const categoryPicker = this.categoryFieldTarget.closest("[data-controller*='category-picker']")
      if (categoryPicker) {
        const selectedCategoryElement = categoryPicker.querySelector("[data-category-picker-target='selectedCategory']")
        if (selectedCategoryElement && analysis.category_matched) {
          selectedCategoryElement.textContent = analysis.category_matched
        }
      }
    }

    // Fill name
    if (analysis.name && this.hasNameFieldTarget) {
      this.nameFieldTarget.value = analysis.name
    }

    // Fill description (should be rich and comprehensive for vector search)
    if (analysis.description && this.hasDescriptionFieldTarget) {
      this.descriptionFieldTarget.value = analysis.description
    }

    // Store the uploaded image reference for later use
    // The image blob ID would be stored separately if needed
    console.log("Form filled with analysis data:", analysis)
  }

  moveToNextStep() {
    // Trigger the form wizard to move to the next step
    if (this.hasNextButtonTarget) {
      this.nextButtonTarget.classList.remove("hidden")
      // Trigger click on next button to advance wizard
      this.nextButtonTarget.click()
    }
  }

  showPreview(file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      this.previewImageTarget.src = e.target.result
      this.previewNameTarget.textContent = file.name
      this.imagePreviewTarget.classList.remove("hidden")
      this.uploadPromptTarget.classList.add("hidden")
    }
    reader.readAsDataURL(file)
  }

  showLoading() {
    this.loadingStateTarget.classList.remove("hidden")
    this.successMessageTarget.classList.add("hidden")
    this.hideError()
  }

  hideLoading() {
    this.loadingStateTarget.classList.add("hidden")
  }

  showSuccess() {
    this.successMessageTarget.classList.remove("hidden")
    this.hideLoading()
  }

  showError(message) {
    this.errorMessageTarget.textContent = message
    this.errorStateTarget.classList.remove("hidden")
    this.hideLoading()
  }

  hideError() {
    this.errorStateTarget.classList.add("hidden")
  }

  retryAnalysis() {
    this.hideError()
    this.hideLoading()
    this.imagePreviewTarget.classList.add("hidden")
    this.uploadPromptTarget.classList.remove("hidden")
    this.fileInputTarget.value = ""
    this.jobId = null
    this.stopPolling()
  }
}

