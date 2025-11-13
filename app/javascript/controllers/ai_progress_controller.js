import { Controller } from "@hotwired/stimulus"
import { createConsumer } from "@rails/actioncable"

// Connects to data-controller="ai-progress"
// Handles real-time progress updates via ActionCable WebSocket
export default class extends Controller {
  static values = {
    userId: String,
    analysisId: String
  }

  static targets = [
    "progressMessage",
    "progressBar",
    "progressPercent",
    "statusIndicator",
    "errorMessage",
    "itemsContainer",
    "completionMessage"
  ]

  connect() {
    this.cable = null
    this.detectionSubscription = null
    this.extractionSubscription = null
    this.setupSubscriptions()
  }

  disconnect() {
    this.unsubscribe()
  }

  setupSubscriptions() {
    // Create ActionCable consumer
    this.cable = createConsumer()

    // Subscribe to detection updates if userId is provided
    if (this.userIdValue) {
      this.detectionSubscription = this.cable.subscriptions.create(
        {
          channel: "AiProcessingChannel",
          user_id: this.userIdValue
        },
        {
          received: (data) => this.handleDetectionUpdate(data),
          connected: () => {
            console.log("Connected to detection channel for user", this.userIdValue)
            this.updateStatusIndicator("connected")
          },
          disconnected: () => {
            console.log("Disconnected from detection channel")
            this.updateStatusIndicator("disconnected")
          }
        }
      )
    }

    // Subscribe to extraction updates if analysisId is provided
    if (this.analysisIdValue) {
      this.extractionSubscription = this.cable.subscriptions.create(
        {
          channel: "AiProcessingChannel",
          analysis_id: this.analysisIdValue
        },
        {
          received: (data) => this.handleExtractionUpdate(data),
          connected: () => {
            console.log("Connected to extraction channel for analysis", this.analysisIdValue)
          },
          disconnected: () => {
            console.log("Disconnected from extraction channel")
          }
        }
      )
    }
  }

  unsubscribe() {
    if (this.detectionSubscription) {
      this.detectionSubscription.unsubscribe()
      this.detectionSubscription = null
    }

    if (this.extractionSubscription) {
      this.extractionSubscription.unsubscribe()
      this.extractionSubscription = null
    }

    if (this.cable) {
      this.cable.disconnect()
      this.cable = null
    }
  }

  handleDetectionUpdate(data) {
    console.log("Detection update received:", data)

    switch (data.type) {
      case "progress_update":
        this.updateProgress(data.message)
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

  handleExtractionUpdate(data) {
    console.log("Extraction update received:", data)

    switch (data.type) {
      case "extraction_progress":
        this.updateExtractionProgress(data)
        break

      case "item_extraction_complete":
        this.handleItemExtractionComplete(data)
        break

      case "item_extraction_failed":
        this.handleItemExtractionFailed(data)
        break

      case "extraction_complete":
        this.handleExtractionComplete(data)
        break

      case "extraction_failed":
        this.handleExtractionError(data.error)
        break

      default:
        console.warn("Unknown extraction update type:", data.type)
    }
  }

  updateProgress(message) {
    if (this.hasProgressMessageTarget) {
      this.progressMessageTarget.textContent = message
      this.progressMessageTarget.classList.remove("hidden")
    }

    this.updateStatusIndicator("processing")
  }

  updateExtractionProgress(data) {
    const message = `Processing ${data.current_item} of ${data.total_items}: ${data.item_name}`
    this.updateProgress(message)

    if (this.hasProgressBarTarget && data.progress_percent !== undefined) {
      this.progressBarTarget.style.width = `${data.progress_percent}%`
    }

    if (this.hasProgressPercentTarget) {
      this.progressPercentTarget.textContent = `${data.progress_percent}%`
    }
  }

  handleDetectionComplete(data) {
    console.log("Detection completed:", data.items_detected, "items found")

    if (this.hasProgressMessageTarget) {
      this.progressMessageTarget.textContent = `Detection complete! Found ${data.items_detected} items.`
    }

    this.updateStatusIndicator("completed")

    // Dispatch custom event for other controllers to handle
    this.dispatch("detection-complete", {
      detail: {
        analysis_id: data.analysis_id,
        items_detected: data.items_detected,
        items: data.items
      }
    })
  }

  handleItemExtractionComplete(data) {
    console.log("Item extraction completed:", data.item_id)

    // Dispatch custom event for individual item completion
    this.dispatch("item-extraction-complete", {
      detail: {
        item_id: data.item_id,
        extraction_result_id: data.extraction_result_id,
        quality_score: data.quality_score
      }
    })
  }

  handleItemExtractionFailed(data) {
    console.error("Item extraction failed:", data.item_id, data.error)

    // Dispatch custom event for item failure
    this.dispatch("item-extraction-failed", {
      detail: {
        item_id: data.item_id,
        error: data.error
      }
    })
  }

  handleExtractionComplete(data) {
    console.log("Extraction completed:", data.successful_items, "items extracted")

    if (this.hasProgressMessageTarget) {
      this.progressMessageTarget.textContent = `Extraction complete! ${data.successful_items} items extracted successfully.`
    }

    if (this.hasCompletionMessageTarget) {
      this.completionMessageTarget.textContent = `Successfully extracted ${data.successful_items} of ${data.total_items} items.`
      this.completionMessageTarget.classList.remove("hidden")
    }

    this.updateStatusIndicator("completed")

    // Dispatch custom event
    this.dispatch("extraction-complete", {
      detail: {
        total_items: data.total_items,
        successful_items: data.successful_items,
        extraction_result_ids: data.extraction_result_ids
      }
    })
  }

  handleDetectionError(error) {
    console.error("Detection error:", error)

    if (this.hasErrorMessageTarget) {
      this.errorMessageTarget.textContent = error
      this.errorMessageTarget.classList.remove("hidden")
    }

    this.updateStatusIndicator("error")

    // Dispatch custom event
    this.dispatch("detection-error", {
      detail: { error }
    })
  }

  handleExtractionError(error) {
    console.error("Extraction error:", error)

    if (this.hasErrorMessageTarget) {
      this.errorMessageTarget.textContent = error
      this.errorMessageTarget.classList.remove("hidden")
    }

    this.updateStatusIndicator("error")

    // Dispatch custom event
    this.dispatch("extraction-error", {
      detail: { error }
    })
  }

  updateStatusIndicator(status) {
    if (!this.hasStatusIndicatorTarget) return

    const indicator = this.statusIndicatorTarget

    // Remove all status classes
    indicator.classList.remove(
      "bg-gray-400",
      "bg-blue-500",
      "bg-green-500",
      "bg-red-500",
      "bg-yellow-500"
    )

    // Add appropriate status class
    switch (status) {
      case "connected":
        indicator.classList.add("bg-blue-500")
        break
      case "processing":
        indicator.classList.add("bg-yellow-500")
        break
      case "completed":
        indicator.classList.add("bg-green-500")
        break
      case "error":
        indicator.classList.add("bg-red-500")
        break
      case "disconnected":
        indicator.classList.add("bg-gray-400")
        break
      default:
        indicator.classList.add("bg-gray-400")
    }
  }
}

