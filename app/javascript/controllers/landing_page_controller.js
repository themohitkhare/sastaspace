import { Controller } from "@hotwired/stimulus"

// Landing page controller with scroll animations and interactivity
export default class extends Controller {
  static targets = ["heroText", "heroImage", "feature", "testimonial"]

  connect() {
    console.log("Landing page controller connected")
    this.setupScrollAnimations()
    this.setupSmoothScrolling()
  }

  disconnect() {
    if (this.observer) {
      this.observer.disconnect()
    }
  }

  setupScrollAnimations() {
    // Use Intersection Observer for performant scroll animations
    const options = {
      threshold: 0.1,
      rootMargin: "0px 0px -100px 0px"
    }

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("animate-fade-in-up")
          // Optional: Stop observing after animation
          this.observer.unobserve(entry.target)
        }
      })
    }, options)

    // Observe all feature and testimonial targets
    this.featureTargets.forEach(el => {
      el.style.opacity = "0"
      el.style.transform = "translateY(20px)"
      this.observer.observe(el)
    })

    this.testimonialTargets.forEach(el => {
      el.style.opacity = "0"
      el.style.transform = "translateY(20px)"
      this.observer.observe(el)
    })
  }

  setupSmoothScrolling() {
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener("click", (e) => {
        const href = anchor.getAttribute("href")
        
        // Don't prevent default for empty hash
        if (href === "#") return
        
        const target = document.querySelector(href)
        if (target) {
          e.preventDefault()
          target.scrollIntoView({
            behavior: "smooth",
            block: "start"
          })
        }
      })
    })
  }
}
