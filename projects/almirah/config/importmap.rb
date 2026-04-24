# Pin npm packages by running ./bin/importmap

pin "application"
pin "@hotwired/turbo-rails", to: "turbo.min.js"
pin "@hotwired/stimulus", to: "stimulus.min.js"
pin "@hotwired/stimulus-loading", to: "stimulus-loading.js"
pin_all_from "app/javascript/controllers", under: "controllers"

# React 18 + ReactDOM via esm.sh — lightweight React islands for ItemCard / Rack.
# No build step required — importmap loads UMD builds from the CDN at runtime.
# In production you'd vendor these to app/assets/javascripts/, but for dev
# the CDN is fine.
pin "react",     to: "https://esm.sh/react@18.3.1"
pin "react-dom", to: "https://esm.sh/react-dom@18.3.1"

# Almirah React components
pin_all_from "app/javascript/almirah", under: "almirah"
