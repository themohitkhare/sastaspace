import { Controller } from "@hotwired/stimulus"
import { createConsumer } from "@rails/actioncable"

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
    analysisResults: Object,
    userId: String  // Add userId for WebSocket subscription
  }

  connect() {
    this.jobId = null
    this.pollingInterval = null
    this.maxPollAttempts = 60 // 2 minutes max (60 * 2 seconds)
    this.pollAttempts = 0
    this.cable = null
    this.subscription = null
    this.userId = null

    // Check for pending extraction job from sessionStorage
    this.checkPendingExtraction()
  }

  disconnect() {
    this.stopPolling()
    this.unsubscribe()
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

      // Store job ID and user ID
      this.jobId = data.data.job_id
      this.userId = this.userIdValue || this.getUserIdFromPage()
      
      // Store job info in sessionStorage for cross-page notifications
      if (this.jobId && this.userId) {
        sessionStorage.setItem('pending_stock_extraction', JSON.stringify({
          job_id: this.jobId,
          user_id: this.userId,
          blob_id: blobIdNum,
          inventory_item_id: inventoryItemId,
          timestamp: Date.now()
        }))
      }

      // Show queued state immediately - user can navigate away
      this.showStatus("Extraction queued... You can navigate away and we'll notify you when it's done.")
      
      // Set up WebSocket subscription for real-time updates
      if (this.userId) {
        this.setupWebSocketSubscription()
      } else {
        // Fallback to polling if WebSocket not available
        this.startPolling()
      }

    } catch (error) {
      console.error("Error starting extraction:", error)
      this.showError(error.message || "Failed to start stock photo extraction")
      if (this.hasButtonTarget) {
        this.buttonTarget.disabled = false
        this.buttonTarget.textContent = "Extract Stock Photo"
      }
    }
  }

  setupWebSocketSubscription() {
    if (!this.userId) {
      console.warn("Cannot setup WebSocket: userId not available")
      return
    }

    // Create ActionCable consumer
    this.cable = createConsumer()

    // Subscribe to stock extraction updates for this user
    this.subscription = this.cable.subscriptions.create(
      {
        channel: "AiProcessingChannel",
        user_id: this.userId
      },
      {
        connected: () => {
          console.log("Connected to stock extraction WebSocket")
        },
        disconnected: () => {
          console.log("Disconnected from stock extraction WebSocket")
        },
        received: (data) => {
          this.handleWebSocketMessage(data)
        }
      }
    )
  }

  unsubscribe() {
    if (this.subscription) {
      this.subscription.unsubscribe()
      this.subscription = null
    }
    if (this.cable) {
      this.cable.disconnect()
      this.cable = null
    }
  }

  handleWebSocketMessage(data) {
    // Only handle messages for our job
    if (data.job_id && data.job_id !== this.jobId) {
      return
    }

    switch (data.type) {
      case "extraction_progress":
        this.showStatus(data.message || "Processing...")
        break

      case "extraction_complete":
        this.stopPolling()
        this.showSuccess(data.data)
        // Clear pending job from sessionStorage
        sessionStorage.removeItem('pending_stock_extraction')
        this.unsubscribe()
        break

      case "extraction_failed":
        this.stopPolling()
        this.showError(data.error || "Extraction failed")
        // Clear pending job from sessionStorage
        sessionStorage.removeItem('pending_stock_extraction')
        this.unsubscribe()
        break

      default:
        console.log("Unknown WebSocket message type:", data.type)
    }
  }

  checkPendingExtraction() {
    const pending = sessionStorage.getItem('pending_stock_extraction')
    if (pending) {
      try {
        const jobInfo = JSON.parse(pending)
        // Check if job is recent (within last hour)
        const oneHourAgo = Date.now() - (60 * 60 * 1000)
        if (jobInfo.timestamp && jobInfo.timestamp > oneHourAgo) {
          this.jobId = jobInfo.job_id
          this.userId = jobInfo.user_id || this.userIdValue || this.getUserIdFromPage()
          
          // Set up WebSocket to listen for completion
          if (this.userId) {
            this.setupWebSocketSubscription()
            this.showStatus("Waiting for extraction to complete...")
          } else {
            // Fallback to polling
            this.startPolling()
          }
        } else {
          // Job is too old, remove it
          sessionStorage.removeItem('pending_stock_extraction')
        }
      } catch (e) {
        console.error("Error parsing pending extraction:", e)
        sessionStorage.removeItem('pending_stock_extraction')
      }
    }
  }

  getUserIdFromPage() {
    // Try to get userId from meta tag or data attribute
    const metaTag = document.querySelector('meta[name="user-id"]')
    if (metaTag) {
      return metaTag.content
    }
    
    // Try to get from data attribute on the element
    const userIdAttr = this.element.dataset.userId
    if (userIdAttr) {
      return userIdAttr
    }
    
    return null
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
          // Clear pending job from sessionStorage
          sessionStorage.removeItem('pending_stock_extraction')
          break

        case "failed":
          this.stopPolling()
          const errorMsg = statusData.error?.message || statusData.error || "Extraction failed"
          this.showError(errorMsg)
          // Clear pending job from sessionStorage
          sessionStorage.removeItem('pending_stock_extraction')
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
    // Only reload if we're still on the same page (not if user navigated away)
    if (window.location.pathname.includes('/inventory_items/')) {
      setTimeout(() => {
        window.location.reload()
      }, 2000) // 2 second delay to show success message
    }
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

