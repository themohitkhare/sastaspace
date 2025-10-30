import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="inventory"
// Handles inventory list filtering, search, view toggle, and bulk actions
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
    "itemCount"
  ]

  static values = {
    viewMode: { type: String, default: "grid" }
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
  }

  disconnect() {
    // Clean up event listeners if needed
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

