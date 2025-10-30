import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="auth"
// Handles form submission, validation, and real-time feedback
export default class extends Controller {
  static targets = [
    "email", "emailError",
    "firstName", "firstNameError",
    "lastName", "lastNameError",
    "password", "passwordError", "passwordStrength", "strengthBar", "strengthText",
    "passwordConfirmation", "passwordConfirmationError",
    "submitButton", "errors"
  ]

  connect() {
    this.passwordStrengthLevels = {
      weak: { text: "Weak", color: "bg-red-500", width: "33%" },
      medium: { text: "Medium", color: "bg-yellow-500", width: "66%" },
      strong: { text: "Strong", color: "bg-green-500", width: "100%" }
    }
  }

  validateEmail() {
    const email = this.emailTarget.value.trim()
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    
    if (!email) {
      this.showError(this.emailErrorTarget, "Email is required")
      return false
    } else if (!emailRegex.test(email)) {
      this.showError(this.emailErrorTarget, "Please enter a valid email address")
      return false
    } else {
      this.clearError(this.emailErrorTarget)
      return true
    }
  }

  validateFirstName() {
    if (!this.hasFirstNameTarget) return true
    
    const firstName = this.firstNameTarget.value.trim()
    if (!firstName) {
      this.showError(this.firstNameErrorTarget, "First name is required")
      return false
    } else if (firstName.length < 2) {
      this.showError(this.firstNameErrorTarget, "First name must be at least 2 characters")
      return false
    } else {
      this.clearError(this.firstNameErrorTarget)
      return true
    }
  }

  validateLastName() {
    if (!this.hasLastNameTarget) return true
    
    const lastName = this.lastNameTarget.value.trim()
    if (!lastName) {
      this.showError(this.lastNameErrorTarget, "Last name is required")
      return false
    } else if (lastName.length < 2) {
      this.showError(this.lastNameErrorTarget, "Last name must be at least 2 characters")
      return false
    } else {
      this.clearError(this.lastNameErrorTarget)
      return true
    }
  }

  validatePassword() {
    if (!this.hasPasswordTarget) return true
    
    const password = this.passwordTarget.value
    
    if (!password) {
      if (this.hasPasswordErrorTarget) {
        this.showError(this.passwordErrorTarget, "Password is required")
      }
      return false
    } else if (password.length < 6) {
      if (this.hasPasswordErrorTarget) {
        this.showError(this.passwordErrorTarget, "Password must be at least 6 characters")
      }
      return false
    } else {
      if (this.hasPasswordErrorTarget) {
        this.clearError(this.passwordErrorTarget)
      }
      return true
    }
  }

  validatePasswordConfirmation() {
    if (!this.hasPasswordConfirmationTarget) return true
    
    const password = this.passwordTarget.value
    const confirmation = this.passwordConfirmationTarget.value
    
    if (!confirmation) {
      this.showError(this.passwordConfirmationErrorTarget, "Please confirm your password")
      return false
    } else if (password !== confirmation) {
      this.showError(this.passwordConfirmationErrorTarget, "Passwords do not match")
      return false
    } else {
      this.clearError(this.passwordConfirmationErrorTarget)
      return true
    }
  }

  checkPasswordStrength() {
    if (!this.hasPasswordTarget || !this.hasPasswordStrengthTarget) return
    
    const password = this.passwordTarget.value
    const strength = this.calculatePasswordStrength(password)
    
    if (strength && this.hasStrengthBarTarget && this.hasStrengthTextTarget) {
      const level = this.passwordStrengthLevels[strength]
      this.strengthBarTarget.style.width = level.width
      this.strengthBarTarget.className = `h-2 rounded-full transition-all duration-300 ${level.color}`
      this.strengthTextTarget.textContent = level.text
    }
  }

  calculatePasswordStrength(password) {
    if (!password || password.length < 6) return null
    
    let strength = 0
    if (password.length >= 8) strength++
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++
    if (/\d/.test(password)) strength++
    if (/[^a-zA-Z\d]/.test(password)) strength++
    
    if (strength <= 1) return "weak"
    if (strength === 2) return "medium"
    return "strong"
  }

  submitForm(event) {
    // Allow default form submission - we're using progressive enhancement
    // The form will submit normally, but we can add client-side validation first
    
    // For registration form, validate all fields
    // For login form, only validate email if present
    let isValid = true
    
    if (this.hasEmailTarget) isValid = this.validateEmail() && isValid
    if (this.hasFirstNameTarget) isValid = this.validateFirstName() && isValid
    if (this.hasLastNameTarget) isValid = this.validateLastName() && isValid
    if (this.hasPasswordTarget && this.hasPasswordConfirmationTarget) {
      // Only validate password confirmation if it exists (registration form)
      isValid = this.validatePassword() && this.validatePasswordConfirmation() && isValid
    } else if (this.hasPasswordTarget) {
      // For login, just check password is not empty
      isValid = this.validatePassword() && isValid
    }
    
    if (!isValid) {
      event.preventDefault()
      return false
    }
    // Defer disabling to next tick so the native submit isn't blocked by a disabled button
    setTimeout(() => {
      if (this.hasSubmitButtonTarget) {
        this.submitButtonTarget.disabled = true
        this.submitButtonTarget.textContent = "Submitting..."
      }
    }, 0)

    return true
  }

  showError(target, message) {
    if (!target) return
    target.textContent = message
    target.classList.remove("hidden")
  }

  clearError(target) {
    if (!target) return
    target.textContent = ""
    target.classList.add("hidden")
  }
}
