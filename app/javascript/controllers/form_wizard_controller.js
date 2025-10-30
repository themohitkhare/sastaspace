import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="form-wizard"
// Handles multi-step form navigation and validation
export default class extends Controller {
  static targets = [
    "step",
    "stepIndicator",
    "nextButton",
    "previousButton",
    "submitButton",
    "progressBar"
  ]

  static values = {
    currentStep: { type: Number, default: 1 },
    totalSteps: { type: Number, default: 4 }
  }

  connect() {
    this.totalStepsValue = this.stepTargets.length
    this.showStep(this.currentStepValue)
    this.updateProgress()
  }

  next() {
    if (this.validateCurrentStep()) {
      if (this.currentStepValue < this.totalStepsValue) {
        this.currentStepValue++
        this.showStep(this.currentStepValue)
        this.updateProgress()
        this.scrollToTop()
      }
    }
  }

  previous() {
    if (this.currentStepValue > 1) {
      this.currentStepValue--
      this.showStep(this.currentStepValue)
      this.updateProgress()
      this.scrollToTop()
    }
  }

  goToStep(stepNumber) {
    if (stepNumber >= 1 && stepNumber <= this.totalStepsValue) {
      this.currentStepValue = stepNumber
      this.showStep(this.currentStepValue)
      this.updateProgress()
      this.scrollToTop()
    }
  }

  showStep(stepNumber) {
    // Hide all steps
    this.stepTargets.forEach((step, index) => {
      step.classList.toggle("hidden", index + 1 !== stepNumber)
    })

    // Update step indicators
    if (this.hasStepIndicatorTargets) {
      this.stepIndicatorTargets.forEach((indicator, index) => {
        const stepNum = index + 1
        indicator.classList.toggle("bg-primary-600", stepNum === stepNumber)
        indicator.classList.toggle("text-white", stepNum === stepNumber)
        indicator.classList.toggle("bg-gray-200", stepNum !== stepNumber)
        indicator.classList.toggle("text-gray-700", stepNum !== stepNumber)
        indicator.classList.toggle("border-primary-500", stepNum <= stepNumber)
        indicator.classList.remove("border-gray-300")
        if (stepNum > stepNumber) {
          indicator.classList.add("border-gray-300")
        }
      })
    }

    // Update navigation buttons
    this.updateNavigationButtons()
  }

  updateNavigationButtons() {
    if (this.hasPreviousButtonTargets) {
      this.previousButtonTargets.forEach(button => {
        button.classList.toggle("hidden", this.currentStepValue === 1)
        button.disabled = this.currentStepValue === 1
      })
    }

    if (this.hasNextButtonTargets) {
      this.nextButtonTargets.forEach(button => {
        button.classList.toggle("hidden", this.currentStepValue === this.totalStepsValue)
      })
    }

    if (this.hasSubmitButtonTargets) {
      this.submitButtonTargets.forEach(button => {
        button.classList.toggle("hidden", this.currentStepValue !== this.totalStepsValue)
      })
    }
  }

  updateProgress() {
    if (this.hasProgressBarTarget) {
      const percentage = (this.currentStepValue / this.totalStepsValue) * 100
      this.progressBarTarget.style.width = `${percentage}%`
    }
  }

  validateCurrentStep() {
    const currentStepElement = this.stepTargets[this.currentStepValue - 1]
    if (!currentStepElement) return true

    // Find all required fields in current step
    const requiredFields = currentStepElement.querySelectorAll("[required]")
    let isValid = true

    requiredFields.forEach(field => {
      if (!field.value || field.value.trim() === "") {
        field.classList.add("border-red-500")
        isValid = false
      } else {
        field.classList.remove("border-red-500")
      }
    })

    // Trigger validation events
    const validationEvent = new CustomEvent("step-validation", {
      detail: { step: this.currentStepValue, valid: isValid }
    })
    this.element.dispatchEvent(validationEvent)

    if (!isValid) {
      this.showStepError("Please fill in all required fields")
    }

    return isValid
  }

  showStepError(message) {
    // Could implement a toast notification here
    const currentStepElement = this.stepTargets[this.currentStepValue - 1]
    if (currentStepElement) {
      let errorDiv = currentStepElement.querySelector(".step-error")
      if (!errorDiv) {
        errorDiv = document.createElement("div")
        errorDiv.className = "step-error mt-4 p-3 bg-red-50 border border-red-200 text-red-800 rounded dark:bg-red-900 dark:border-red-700 dark:text-red-200"
        currentStepElement.appendChild(errorDiv)
      }
      errorDiv.textContent = message
      setTimeout(() => {
        errorDiv.remove()
      }, 5000)
    }
  }

  scrollToTop() {
    window.scrollTo({ top: 0, behavior: "smooth" })
  }
}

