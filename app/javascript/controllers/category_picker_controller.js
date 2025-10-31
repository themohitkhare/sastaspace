import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="category-picker"
// Handles hierarchical category selection with breadcrumbs and tree navigation
export default class extends Controller {
  static targets = [
    "modal",
    "categoryTree",
    "selectedCategory",
    "hiddenInput",
    "breadcrumbs",
    "searchInput",
    "categoryList",
    "backButton"
  ]

  static values = {
    selectedId: { type: Number, default: null },
    apiUrl: { type: String, default: "/api/v1/categories" }
  }

  connect() {
    this.categories = []
    this.allCategories = [] // Store all categories for filtering
    this.currentPath = []
    this.loadCategories()
  }

  open() {
    if (this.hasModalTarget) {
      this.modalTarget.classList.remove("hidden")
      document.body.style.overflow = "hidden"
      // Reset to root view when opening
      this.currentPath = []
      this.updateBreadcrumbs()
      // Load all categories instead of just roots for easier browsing
      this.loadAllCategories()
    }
  }

  close() {
    if (this.hasModalTarget) {
      this.modalTarget.classList.add("hidden")
      document.body.style.overflow = ""
    }
  }

  async loadCategories(parentId = null) {
    try {
      const url = parentId 
        ? `${this.apiUrlValue}/${parentId}/children`
        : `${this.apiUrlValue}/roots`

      const response = await fetch(url, {
        headers: {
          "Accept": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin"
      })

      if (!response.ok) {
        throw new Error("Failed to load categories")
      }

      const data = await response.json()
      // API responds with { success, data: { categories: [...] } }
      // Older variants may return { categories: [...] }
      this.categories = (data.data && data.data.categories) || data.categories || []
      this.renderCategories()
    } catch (error) {
      console.error("Error loading categories:", error)
      this.showError("Failed to load categories. Please try again.")
    }
  }

  async loadAllCategories() {
    try {
      // Load all categories (not just roots)
      const url = `${this.apiUrlValue}`

      const response = await fetch(url, {
        headers: {
          "Accept": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin"
      })

      if (!response.ok) {
        throw new Error("Failed to load categories")
      }

      const data = await response.json()
      this.allCategories = (data.data && data.data.categories) || data.categories || []
      this.categories = this.allCategories // Show all categories by default
      this.renderCategories()
    } catch (error) {
      console.error("Error loading all categories:", error)
      // Fallback to roots if loading all fails
      this.loadCategories()
    }
  }

  renderCategories() {
    if (!this.hasCategoryListTarget) return

    const list = this.categoryListTarget
    list.innerHTML = ""

    if (this.categories.length === 0) {
      list.innerHTML = '<li class="px-4 py-2 text-gray-500 dark:text-gray-400">No categories found</li>'
      return
    }

    this.categories.forEach(category => {
      const item = this.buildCategoryItem(category)
      list.appendChild(item)
    })
  }

  buildCategoryItem(category) {
    const li = document.createElement("li")
    li.className = "px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer border-b border-gray-200 dark:border-gray-700"
    
    const div = document.createElement("div")
    div.className = "flex items-center justify-between"

    const infoDiv = document.createElement("div")
    infoDiv.className = "flex-1"

    const nameSpan = document.createElement("span")
    nameSpan.className = "text-gray-900 dark:text-white font-medium"
    nameSpan.textContent = category.name

    const countSpan = document.createElement("span")
    countSpan.className = "text-sm text-gray-500 dark:text-gray-400 ml-2"
    countSpan.textContent = category.item_count ? `(${category.item_count})` : ""

    infoDiv.appendChild(nameSpan)
    infoDiv.appendChild(countSpan)

    // Check if category has children
    if (category.has_children || category.children_count > 0) {
      const arrowIcon = document.createElement("svg")
      arrowIcon.className = "w-5 h-5 text-gray-400"
      arrowIcon.fill = "none"
      arrowIcon.stroke = "currentColor"
      arrowIcon.viewBox = "0 0 24 24"
      arrowIcon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>'

      div.appendChild(infoDiv)
      div.appendChild(arrowIcon)

      li.addEventListener("click", () => {
        this.navigateToCategory(category)
      })
    } else {
      // Leaf category - can be selected
      div.appendChild(infoDiv)
      
      li.addEventListener("click", () => {
        this.selectCategory(category)
      })
    }

    li.appendChild(div)
    return li
  }

  navigateToCategory(category) {
    this.currentPath.push(category)
    this.updateBreadcrumbs()
    this.loadCategories(category.id)
  }

  async selectCategory(category) {
    this.selectedIdValue = category.id
    
    if (this.hasSelectedCategoryTarget) {
      this.selectedCategoryTarget.textContent = category.name
      this.selectedCategoryTarget.dataset.categoryId = category.id
    }

    // Update hidden input field value for form submission
    if (this.hasHiddenInputTarget) {
      this.hiddenInputTarget.value = category.id
      // Trigger change/input events to notify any listeners/validation
      this.hiddenInputTarget.dispatchEvent(new Event("input", { bubbles: true }))
      this.hiddenInputTarget.dispatchEvent(new Event("change", { bubbles: true }))
    }

    // Trigger change event
    const event = new CustomEvent("category-selected", {
      detail: { category: category }
    })
    this.element.dispatchEvent(event)

    this.close()
  }

  updateBreadcrumbs() {
    if (!this.hasBreadcrumbsTarget) return

    const breadcrumbs = this.breadcrumbsTarget
    breadcrumbs.innerHTML = ""

    // Only show breadcrumbs if we're in a subcategory (navigated into a category)
    // When showing all categories, hide breadcrumbs entirely
    if (this.currentPath.length === 0) {
      breadcrumbs.classList.add("hidden")
      return
    }

    breadcrumbs.classList.remove("hidden")

    // Path breadcrumbs (only shown when navigating into subcategories)
    this.currentPath.forEach((category, index) => {
      if (index > 0) {
        const separator = document.createElement("span")
        separator.className = "mx-2 text-gray-400"
        separator.textContent = "/"
        breadcrumbs.appendChild(separator)
      }

      const item = document.createElement("span")
      if (index === this.currentPath.length - 1) {
        item.className = "text-gray-700 dark:text-gray-300 font-medium"
        item.textContent = category.name
      } else {
        item.className = "cursor-pointer text-primary-600 dark:text-primary-400 hover:underline"
        item.textContent = category.name
        item.addEventListener("click", () => {
          this.currentPath = this.currentPath.slice(0, index + 1)
          this.updateBreadcrumbs()
          this.loadCategories(category.id)
        })
      }
      breadcrumbs.appendChild(item)
    })

    // Show/hide back button
    if (this.hasBackButtonTarget) {
      this.backButtonTarget.classList.toggle("hidden", this.currentPath.length === 0)
    }
  }

  goBack() {
    if (this.currentPath.length > 0) {
      this.currentPath.pop()
      const parentId = this.currentPath.length > 0 
        ? this.currentPath[this.currentPath.length - 1].id 
        : null
      this.updateBreadcrumbs()
      this.loadCategories(parentId)
    }
  }

  searchCategories(event) {
    const query = event.target.value.trim()
    if (!query || query.length < 2) {
      // If search is cleared, show all categories again
      this.categories = this.allCategories.length > 0 ? this.allCategories : this.categories
      this.renderCategories()
      return
    }

    // Filter from all categories (not just currently displayed ones)
    const sourceCategories = this.allCategories.length > 0 ? this.allCategories : this.categories
    const filtered = sourceCategories.filter(cat => 
      cat.name.toLowerCase().includes(query.toLowerCase())
    )
    
    this.categories = filtered
    this.renderCategories()
    
    // If no results and we haven't loaded all categories yet, try API search
    if (filtered.length === 0 && this.allCategories.length === 0) {
      this.searchCategoriesAPI(query)
    }
  }

  async searchCategoriesAPI(query) {
    try {
      const response = await fetch(`${this.apiUrlValue}?search=${encodeURIComponent(query)}`, {
        headers: {
          "Accept": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin"
      })

      if (!response.ok) {
        throw new Error("Search failed")
      }

      const data = await response.json()
      this.categories = (data.data && data.data.categories) || data.categories || []
      this.renderCategories()
    } catch (error) {
      console.error("Error searching categories:", error)
    }
  }

  showError(message) {
    // Could implement a toast notification here
    console.error(message)
  }

  // Prevent modal close when clicking inside
  preventClose(event) {
    event.stopPropagation()
  }
}

