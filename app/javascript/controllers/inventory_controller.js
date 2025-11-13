import { Controller } from "@hotwired/stimulus"
import { createConsumer } from "@rails/actioncable"

// Connects to data-controller="inventory"
// Handles inventory list filtering, search, view toggle, bulk actions, and processing notifications
export default class extends Controller {
  static targets = [
    "gridView",
    "listView",
    "gridToggle",
    "listToggle",
    "searchInput",
    "categoryFilter",
    "typeFilter",
    "colorFilter",
    "seasonFilter",
    "filterForm",
    "itemCard",
    "bulkCheckbox",
    "selectAllCheckbox",
    "bulkActionsBar",
    "itemCount",
    "processingIndicator",
    "processingMessage"
  ]

  static values = {
    viewMode: { type: String, default: "grid" },
    userId: String
  }

  connect() {
    // Restore view mode from localStorage, default to grid
    const savedViewMode = localStorage.getItem("inventoryViewMode")
    const initialMode = savedViewMode && (savedViewMode === "grid" || savedViewMode === "list") ? savedViewMode : "grid"
    this.viewModeValue = initialMode
    this.toggleView(initialMode)

    // Apply real-time search
    if (this.hasSearchInputTarget) {
      this.searchInputTarget.addEventListener("input", this.debounce(() => {
        this.applyFilters()
      }, 300).bind(this))
    }

    // Check for pending detection job and set up WebSocket
    this.checkPendingDetection()
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

  checkPendingDetection() {
    // Check sessionStorage for pending detection job
    const pendingJob = sessionStorage.getItem('pending_detection_job')
    if (pendingJob) {
      try {
        const jobData = JSON.parse(pendingJob)
        this.userId = jobData.user_id || this.userIdValue
        this.jobId = jobData.job_id
        this.blobId = jobData.blob_id

        // Show processing indicator
        this.showProcessingIndicator()

        // Set up WebSocket subscription
        if (this.userId) {
          this.setupWebSocketSubscription()
        }
      } catch (e) {
        console.error("Error parsing pending job data:", e)
        sessionStorage.removeItem('pending_detection_job')
      }
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
        this.updateProcessingMessage(data.message)
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

  handleDetectionComplete(data) {
    console.log("Detection completed:", data.items_detected, "items found,", data.created_items_count || 0, "items created")

    // Clear pending job from sessionStorage
    sessionStorage.removeItem('pending_detection_job')

    // Hide processing indicator
    this.hideProcessingIndicator()

    // Show success notification with created items count
    const createdCount = data.created_items_count || data.items_detected || 0
    this.showSuccessNotification(createdCount)

    // Unsubscribe from WebSocket
    this.unsubscribe()

    // Reload the page to show new items (with a slight delay to show notification)
    setTimeout(() => {
      window.location.reload()
    }, 1500) // Reload after 1.5 seconds to show notification
  }

  handleDetectionError(error) {
    console.error("Detection error:", error)

    // Clear pending job from sessionStorage
    sessionStorage.removeItem('pending_detection_job')

    // Hide processing indicator
    this.hideProcessingIndicator()

    // Show error notification
    this.showErrorNotification(error || "Failed to detect clothing items")

    // Unsubscribe from WebSocket
    this.unsubscribe()
  }

  showProcessingIndicator() {
    if (this.hasProcessingIndicatorTarget) {
      this.processingIndicatorTarget.classList.remove("hidden")
    }
    this.updateProcessingMessage("Analyzing image for clothing items...")
  }

  hideProcessingIndicator() {
    if (this.hasProcessingIndicatorTarget) {
      this.processingIndicatorTarget.classList.add("hidden")
    }
  }

  updateProcessingMessage(message) {
    if (this.hasProcessingMessageTarget) {
      this.processingMessageTarget.textContent = message
    }
  }

  showSuccessNotification(itemsCount) {
    // Create a temporary success notification
    const notification = document.createElement("div")
    notification.className = "fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2"
    notification.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
      </svg>
      <span>Successfully detected ${itemsCount} item${itemsCount !== 1 ? 's' : ''}!</span>
    `
    document.body.appendChild(notification)

    setTimeout(() => {
      notification.remove()
    }, 5000)
  }

  showErrorNotification(message) {
    // Create a temporary error notification
    const notification = document.createElement("div")
    notification.className = "fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2"
    notification.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
      </svg>
      <span>${message}</span>
    `
    document.body.appendChild(notification)

    setTimeout(() => {
      notification.remove()
    }, 5000)
  }

  switchToGridView() {
    this.viewModeValue = "grid"
    this.toggleView("grid")
    localStorage.setItem("inventoryViewMode", "grid")
  }

  switchToListView() {
    this.viewModeValue = "list"
    this.toggleView("list")
    localStorage.setItem("inventoryViewMode", "list")
  }

  toggleView(mode) {
    if (this.hasGridViewTarget) {
      this.gridViewTarget.classList.toggle("hidden", mode !== "grid")
    }
    if (this.hasListViewTarget) {
      this.listViewTarget.classList.toggle("hidden", mode !== "list")
    }
    if (this.hasGridToggleTarget) {
      this.gridToggleTarget.classList.toggle("bg-primary-600", mode === "grid")
      this.gridToggleTarget.classList.toggle("text-white", mode === "grid")
      this.gridToggleTarget.classList.toggle("bg-gray-200", mode !== "grid")
      this.gridToggleTarget.classList.toggle("text-gray-700", mode !== "grid")
    }
    if (this.hasListToggleTarget) {
      this.listToggleTarget.classList.toggle("bg-primary-600", mode === "list")
      this.listToggleTarget.classList.toggle("text-white", mode === "list")
      this.listToggleTarget.classList.toggle("bg-gray-200", mode !== "list")
      this.listToggleTarget.classList.toggle("text-gray-700", mode !== "list")
    }
  }

  applyFilters() {
    // Submit the filter form to apply filters
    if (this.hasFilterFormTarget) {
      this.filterFormTarget.requestSubmit()
    }
  }

  clearFilters() {
    // Clear all filter inputs
    if (this.hasSearchInputTarget) {
      this.searchInputTarget.value = ""
    }
    if (this.hasCategoryFilterTarget) {
      this.categoryFilterTarget.value = ""
    }
    if (this.hasTypeFilterTarget) {
      this.typeFilterTarget.value = ""
    }
    if (this.hasColorFilterTarget) {
      this.colorFilterTarget.value = ""
    }
    if (this.hasSeasonFilterTarget) {
      this.seasonFilterTarget.value = ""
    }

    // Submit form to clear filters
    this.applyFilters()
  }

  toggleSelectAll(event) {
    const checked = event.target.checked
    if (this.hasBulkCheckboxTargets) {
      this.bulkCheckboxTargets.forEach(checkbox => {
        checkbox.checked = checked
      })
    }
    this.updateBulkActionsBar()
  }

  toggleItemSelection() {
    this.updateBulkActionsBar()
    this.updateSelectAllCheckbox()
  }

  updateBulkActionsBar() {
    const selectedCount = this.selectedItems().length
    if (this.hasBulkActionsBarTarget) {
      this.bulkActionsBarTarget.classList.toggle("hidden", selectedCount === 0)
      if (this.hasItemCountTarget && selectedCount > 0) {
        this.itemCountTarget.textContent = `${selectedCount} item${selectedCount === 1 ? "" : "s"} selected`
      }
    }
  }

  updateSelectAllCheckbox() {
    if (this.hasBulkCheckboxTargets && this.hasSelectAllCheckboxTarget) {
      const totalCount = this.bulkCheckboxTargets.length
      const selectedCount = this.selectedItems().length
      this.selectAllCheckboxTarget.checked = totalCount > 0 && selectedCount === totalCount
      this.selectAllCheckboxTarget.indeterminate = selectedCount > 0 && selectedCount < totalCount
    }
  }

  selectedItems() {
    if (!this.hasBulkCheckboxTargets) return []
    return this.bulkCheckboxTargets
      .filter(checkbox => checkbox.checked)
      .map(checkbox => checkbox.value)
  }

  bulkDelete() {
    const selectedIds = this.selectedItems()
    if (selectedIds.length === 0) return

    if (confirm(`Are you sure you want to delete ${selectedIds.length} item(s)?`)) {
      // Create a form and submit it
      const form = document.createElement("form")
      form.method = "POST"
      form.action = "/inventory_items/bulk_delete"

      // Add CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content
      if (csrfToken) {
        const csrfInput = document.createElement("input")
        csrfInput.type = "hidden"
        csrfInput.name = "authenticity_token"
        csrfInput.value = csrfToken
        form.appendChild(csrfInput)
      }

      // Add method override
      const methodInput = document.createElement("input")
      methodInput.type = "hidden"
      methodInput.name = "_method"
      methodInput.value = "DELETE"
      form.appendChild(methodInput)

      // Add selected IDs
      selectedIds.forEach(id => {
        const idInput = document.createElement("input")
        idInput.type = "hidden"
        idInput.name = "item_ids[]"
        idInput.value = id
        form.appendChild(idInput)
      })

      document.body.appendChild(form)
      form.submit()
    }
  }

  // Debounce helper function
  debounce(func, wait) {
    let timeout
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout)
        func(...args)
      }
      clearTimeout(timeout)
      timeout = setTimeout(later, wait)
    }
  }
}

