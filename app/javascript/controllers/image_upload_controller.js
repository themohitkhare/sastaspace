import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="image-upload"
// Handles drag & drop image upload, preview, progress indicators, and image reordering
export default class extends Controller {
  static targets = [
    "dropZone",
    "fileInput",
    "previewContainer",
    "progressBar",
    "progressText",
    "primaryPreview",
    "additionalPreviews",
    "errorMessage"
  ]

  static values = {
    maxSize: { type: Number, default: 5242880 }, // 5MB in bytes
    acceptedTypes: { type: Array, default: ["image/jpeg", "image/jpg", "image/png", "image/webp"] },
    maxFiles: { type: Number, default: 10 }
  }

  connect() {
    this.setupDragAndDrop()
    this.files = []
    this.previewFiles = []
  }

  setupDragAndDrop() {
    if (!this.hasDropZoneTarget) return

    const dropZone = this.dropZoneTarget

    // Prevent default drag behaviors
    ;["dragenter", "dragover", "dragleave", "drop"].forEach(eventName => {
      dropZone.addEventListener(eventName, this.preventDefaults.bind(this), false)
      document.body.addEventListener(eventName, this.preventDefaults.bind(this), false)
    })

    // Highlight drop zone when item is dragged over it
    ;["dragenter", "dragover"].forEach(eventName => {
      dropZone.addEventListener(
        eventName,
        () => {
          dropZone.classList.add("border-primary-500", "bg-primary-50", "dark:bg-primary-900")
        },
        false
      )
    })

    ;["dragleave", "drop"].forEach(eventName => {
      dropZone.addEventListener(
        eventName,
        () => {
          dropZone.classList.remove("border-primary-500", "bg-primary-50", "dark:bg-primary-900")
        },
        false
      )
    })

    // Handle dropped files
    dropZone.addEventListener(
      "drop",
      (e) => {
        const files = e.dataTransfer.files
        this.handleFiles(files)
      },
      false
    )
  }

  preventDefaults(e) {
    e.preventDefault()
    e.stopPropagation()
  }

  selectFiles(event) {
    if (event && event.currentTarget && event.currentTarget.files) {
      this.handleFiles(event.currentTarget.files)
    } else if (event && event.target && event.target.files) {
      this.handleFiles(event.target.files)
    }
  }

  handleFiles(files) {
    const fileArray = Array.from(files)
    const validFiles = fileArray.filter(file => this.validateFile(file))

    if (validFiles.length === 0) {
      this.showError("No valid image files selected")
      return
    }

    // Check total file count
    if (this.previewFiles.length + validFiles.length > this.maxFilesValue) {
      this.showError(`Maximum ${this.maxFilesValue} files allowed`)
      return
    }

    validFiles.forEach(file => {
      this.previewFiles.push(file)
      this.createPreview(file)
      this.updateFileInput()
    })
  }

  validateFile(file) {
    // Check file type
    if (!this.acceptedTypesValue.includes(file.type)) {
      this.showError(`${file.name} is not a valid image type`)
      return false
    }

    // Check file size
    if (file.size > this.maxSizeValue) {
      this.showError(`${file.name} exceeds the maximum size of ${(this.maxSizeValue / 1024 / 1024).toFixed(1)}MB`)
      return false
    }

    return true
  }

  createPreview(file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      const preview = this.buildPreviewElement(e.target.result, file.name, file)
      if (this.hasAdditionalPreviewsTarget) {
        this.additionalPreviewsTarget.appendChild(preview)
      } else if (this.hasPrimaryPreviewTarget) {
        this.updatePrimaryPreview(e.target.result, file)
      }
    }
    reader.readAsDataURL(file)
  }

  buildPreviewElement(src, filename, file) {
    const container = document.createElement("div")
    container.className = "relative group"
    container.dataset.filename = filename

    const img = document.createElement("img")
    img.src = src
    img.className = "w-full h-full object-cover rounded-lg"
    img.alt = filename

    const overlay = document.createElement("div")
    overlay.className = "absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 rounded-lg transition-opacity flex items-center justify-center"

    const removeButton = document.createElement("button")
    removeButton.type = "button"
    removeButton.className = "hidden group-hover:block text-white bg-red-600 hover:bg-red-700 rounded-full p-2"
    removeButton.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
      </svg>
    `
    removeButton.addEventListener("click", () => {
      this.removePreview(filename)
    })

    overlay.appendChild(removeButton)
    container.appendChild(img)
    container.appendChild(overlay)

    return container
  }

  updatePrimaryPreview(src, file) {
    if (this.hasPrimaryPreviewTarget) {
      this.primaryPreviewTarget.innerHTML = `
        <img src="${src}" alt="Preview" class="w-full h-full object-cover rounded-lg">
        <button type="button" data-action="click->image-upload#removePrimary" 
                class="absolute top-2 right-2 bg-red-600 text-white rounded-full p-2 hover:bg-red-700">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      `
      this.previewFiles = [file] // Only one primary image
    }
  }

  removePreview(filename) {
    this.previewFiles = this.previewFiles.filter(f => f.name !== filename)
    const previewElement = this.additionalPreviewsTarget?.querySelector(`[data-filename="${filename}"]`)
    if (previewElement) {
      previewElement.remove()
    }
    this.updateFileInput()
  }

  removePrimary() {
    this.previewFiles = []
    if (this.hasPrimaryPreviewTarget) {
      this.primaryPreviewTarget.innerHTML = ""
    }
    if (this.hasFileInputTarget) {
      this.fileInputTarget.value = ""
    }
  }

  updateFileInput() {
    // For multiple files, we'll use FormData on submit
    // The file input will be populated via JavaScript FormData
  }

  showError(message) {
    if (this.hasErrorMessageTarget) {
      this.errorMessageTarget.textContent = message
      this.errorMessageTarget.classList.remove("hidden")
      setTimeout(() => {
        this.errorMessageTarget.classList.add("hidden")
      }, 5000)
    }
  }

  clearError() {
    if (this.hasErrorMessageTarget) {
      this.errorMessageTarget.classList.add("hidden")
      this.errorMessageTarget.textContent = ""
    }
  }

  getFilesForUpload() {
    return this.previewFiles
  }
}

