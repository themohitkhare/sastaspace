Rails.application.routes.draw do
  # Health check — used by kamal-proxy and uptime monitors.
  get "up" => "rails/health#show", as: :rails_health_check

  # Authentication — Rails 8 built-in session management.
  resource  :session, only: [ :new, :create, :destroy ]
  resources :passwords, param: :token, only: [ :new, :create, :edit, :update ]

  # Google OAuth callback — all apps share this one route on sastaspace.com.
  # OmniAuth 2.x requires a POST to /auth/google to initiate, then Google
  # redirects back here via GET (or POST depending on config).
  get  "/auth/google/callback", to: "omniauth_callbacks#google_oauth2"
  post "/auth/google/callback", to: "omniauth_callbacks#google_oauth2"
  get  "/auth/failure",         to: "omniauth_callbacks#failure"

  # Home page — project card grid + hero.
  root "pages#home"

  # Admin dashboard — gated by current_user.admin? in AdminController.
  get "/admin" => "admin#index", as: :admin_root
end
