import { Application } from "@hotwired/stimulus"

const application = Application.start()

// Configure Stimulus development experience
// In Rails with importmap, we check the hostname instead of process.env
application.debug = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.hostname.includes("lvh.me")
window.Stimulus   = application

export { application }
