import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="stock-photo-extraction"
export default class extends Controller {
  static targets = [
    "button",
    "status",
    "progress",
    "extractedImage",
    "errorMessage"
  ]

  static values = {
    blobId: Number,  // Changed from String to Number to ensure correct type
    inventoryItemId: Number,  // Add inventory_item_id to ensure we update the correct item
    analysisResults: Object
  }

  connect() {
    this.jobId = null
    this.pollingInterval = null
    this.maxPollAttempts = 60 // 2 minutes max (60 * 2 seconds)
    this.pollAttempts = 0
  }

  disconnect() {
    this.stopPolling()
  }

  async extractStockPhoto(event) {
    // Prevent form submission if button is inside a form
    if (event) {
      event.preventDefault()
      event.stopPropagation()
    }
    
    // Get data from Stimulus values
    let blobId = this.blobIdValue
    let analysisResults = this.analysisResultsValue

    // Debug logging
    console.log("ExtractStockPhoto - Debug Info:")
    console.log("  blobIdValue:", blobId)
    console.log("  blobIdValue type:", typeof blobId)
    console.log("  element.dataset:", this.element.dataset)
    console.log("  data-debug-item-id:", this.element.dataset.debugItemId)
    console.log("  data-debug-blob-id:", this.element.dataset.debugBlobId)
    console.log("  analysisResults:", analysisResults)

    // Fallback: If Stimulus value is missing or invalid, try reading from data attribute directly
    if (!blobId || blobId === 0 || blobId === "0") {
      const debugBlobId = this.element.dataset.debugBlobId
      if (debugBlobId) {
        console.warn("Stimulus blobIdValue is invalid, using data-debug-blob-id:", debugBlobId)
        blobId = Number(debugBlobId)
      } else {
        // Try reading from the Stimulus data attribute directly
        const attrName = this.constructor.identifier + "-blob-id-value"
        const attrValue = this.element.getAttribute(`data-${attrName}`)
        if (attrValue) {
          console.warn("Using direct attribute value:", attrValue)
          blobId = Number(attrValue)
        }
      }
    }

    if (!blobId || blobId === 0 || isNaN(Number(blobId))) {
      console.error("No valid blob ID found. blobId:", blobId)
      this.showError("Image blob ID is required. Please refresh the page and try again.")
      return
    }

    if (!analysisResults) {
      this.showError("Analysis results are required")
      return
    }

    // Stimulus Object values should automatically parse JSON, but handle string case
    if (typeof analysisResults === "string") {
      try {
        // Trim and clean the string in case of encoding issues
        const cleaned = analysisResults.trim()
        // Remove any leading/trailing whitespace or invalid characters
        const jsonStart = cleaned.indexOf('{')
        const jsonEnd = cleaned.lastIndexOf('}')
        if (jsonStart >= 0 && jsonEnd > jsonStart) {
          analysisResults = JSON.parse(cleaned.substring(jsonStart, jsonEnd + 1))
        } else {
          analysisResults = JSON.parse(cleaned)
        }
      } catch (e) {
        console.error("JSON parse error:", e)
        console.error("Raw analysisResults:", analysisResults)
        console.error("Type:", typeof analysisResults)
        this.showError(`Invalid analysis results format: ${e.message}`)
        return
      }
    }

    // Disable button and show loading
    if (this.hasButtonTarget) {
      this.buttonTarget.disabled = true
      this.buttonTarget.textContent = "Extracting..."
    }

    this.hideError()
    this.showStatus("Starting extraction...")

    try {
      // Ensure blobId is a number
      const blobIdNum = Number(blobId)
      if (isNaN(blobIdNum) || blobIdNum <= 0) {
        console.error("Invalid blob_id:", blobId, "converted to:", blobIdNum)
        this.showError(`Invalid image blob ID: ${blobId}`)
        if (this.hasButtonTarget) {
          this.buttonTarget.disabled = false
          this.buttonTarget.textContent = "Extract Stock Photo"
        }
        return
      }
      
      // Get inventory_item_id if available (for more precise item lookup)
      const inventoryItemId = this.inventoryItemIdValue || null
      console.log("Sending to API - blob_id:", blobIdNum, "inventory_item_id:", inventoryItemId, "(original:", blobId, ", type:", typeof blobId, ")")
      
      // Call extraction API
      const response = await fetch("/api/v1/stock_extraction/extract", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include",
        body: JSON.stringify({
          blob_id: blobIdNum,
          inventory_item_id: inventoryItemId,  // Pass inventory_item_id for precise lookup
          analysis_results: analysisResults
        })
      })

      const data = await response.json()

      if (!response.ok || !data.success) {
        throw new Error(data.error?.message || data.error?.code || "Failed to start extraction")
      }

      // Store job ID and start polling
      this.jobId = data.data.job_id
      this.showStatus("Extraction in progress...")
      this.startPolling()

    } catch (error) {
      console.error("Error starting extraction:", error)
      this.showError(error.message || "Failed to start stock photo extraction")
      if (this.hasButtonTarget) {
        this.buttonTarget.disabled = false
        this.buttonTarget.textContent = "Extract Stock Photo"
      }
    }
  }

  startPolling() {
    this.pollAttempts = 0
    this.pollingInterval = setInterval(() => {
      this.checkStatus()
    }, 2000) // Poll every 2 seconds
  }

  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval)
      this.pollingInterval = null
    }
  }

  async checkStatus() {
    if (!this.jobId) {
      this.stopPolling()
      return
    }

    this.pollAttempts++

    if (this.pollAttempts > this.maxPollAttempts) {
      this.stopPolling()
      this.showError("Extraction timed out. Please try again.")
      if (this.hasButtonTarget) {
        this.buttonTarget.disabled = false
        this.buttonTarget.textContent = "Extract Stock Photo"
      }
      return
    }

    try {
      const response = await fetch(`/api/v1/stock_extraction/status/${this.jobId}`, {
        method: "GET",
        headers: {
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        credentials: "include"
      })

      const data = await response.json()

      if (!response.ok || !data.success) {
        throw new Error(data.error?.message || "Failed to check status")
      }

      const statusData = data.data

      switch (statusData.status) {
        case "processing":
          this.showStatus("Processing... (this may take 30-60 seconds)")
          break

        case "completed":
          this.stopPolling()
          this.showSuccess(statusData.data)
          break

        case "failed":
          this.stopPolling()
          const errorMsg = statusData.error?.message || statusData.error || "Extraction failed"
          this.showError(errorMsg)
          if (this.hasButtonTarget) {
            this.buttonTarget.disabled = false
            this.buttonTarget.textContent = "Extract Stock Photo"
          }
          break

        case "not_found":
          this.stopPolling()
          this.showError("Extraction job not found")
          if (this.hasButtonTarget) {
            this.buttonTarget.disabled = false
            this.buttonTarget.textContent = "Extract Stock Photo"
          }
          break

        default:
          // Keep polling
          break
      }
    } catch (error) {
      console.error("Error checking extraction status:", error)
      // Don't stop polling on transient errors, but log them
      if (this.pollAttempts > 10) {
        // After 10 attempts, if we're still getting errors, stop
        this.stopPolling()
        this.showError("Error checking extraction status. Please refresh the page.")
        if (this.hasButtonTarget) {
          this.buttonTarget.disabled = false
          this.buttonTarget.textContent = "Extract Stock Photo"
        }
      }
    }
  }

  showStatus(message) {
    if (this.hasStatusTarget) {
      this.statusTarget.textContent = message
      this.statusTarget.classList.remove("hidden")
    }
    if (this.hasProgressTarget) {
      this.progressTarget.classList.remove("hidden")
    }
  }

  showSuccess(data) {
    this.hideStatus()

    // Show success message
    const successMessage = data.primary_image_replaced
      ? "✓ Stock photo extracted successfully! Primary image has been replaced with the extracted image. Original image moved to additional images."
      : "✓ Stock photo extracted successfully! The extracted image has been saved."

    if (this.hasExtractedImageTarget) {
      this.extractedImageTarget.innerHTML = `
        <div class="p-4 bg-green-50 border border-green-200 rounded-lg dark:bg-green-900 dark:border-green-700">
          <p class="text-green-800 dark:text-green-200">
            ${successMessage}
          </p>
          <p class="text-sm text-green-600 dark:text-green-300 mt-2">
            Refreshing page to show updated image...
          </p>
        </div>
      `
      this.extractedImageTarget.classList.remove("hidden")
    }

    if (this.hasButtonTarget) {
      this.buttonTarget.disabled = false
      this.buttonTarget.textContent = "Extract Stock Photo"
    }

    // Reload the page after a short delay to show the updated primary image
    // This ensures the user sees the new extracted image as the primary
    setTimeout(() => {
      window.location.reload()
    }, 2000) // 2 second delay to show success message
  }

  showError(message) {
    this.hideStatus()
    
    if (this.hasErrorMessageTarget) {
      this.errorMessageTarget.textContent = message
      this.errorMessageTarget.classList.remove("hidden")
    }
  }

  hideStatus() {
    if (this.hasStatusTarget) {
      this.statusTarget.classList.add("hidden")
    }
    if (this.hasProgressTarget) {
      this.progressTarget.classList.add("hidden")
    }
  }

  hideError() {
    if (this.hasErrorMessageTarget) {
      this.errorMessageTarget.classList.add("hidden")
    }
  }
}

