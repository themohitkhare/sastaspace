Rails.application.routes.draw do
  # All routes are explicitly scoped under /almirah because kamal-proxy
  # forwards the full request path to the container (no SCRIPT_NAME rewrite).
  # config.relative_url_root = "/almirah" only affects URL *generation*; it
  # does not strip the prefix from incoming PATH_INFO. So every route has
  # to live under the /almirah scope for request matching to succeed.
  scope path: "/almirah" do
    # Health check — used by kamal-proxy and uptime monitors.
    get "up" => "rails/health#show", as: :rails_health_check

    # Authentication — Rails 8 built-in session management.
    resource  :session, only: [ :new, :create, :destroy ]
    resources :passwords, param: :token, only: [ :new, :create, :edit, :update ]

    # Google OAuth callback
    get  "/auth/google/callback", to: "omniauth_callbacks#google_oauth2"
    post "/auth/google/callback", to: "omniauth_callbacks#google_oauth2"
    get  "/auth/failure",         to: "omniauth_callbacks#failure"

    # Almirah rack home — mounted at /almirah
    root "rack#index", as: :root

    # Item detail
    resources :items, only: [ :show ]

    # Profile / me page (ERB)
    get "me",       to: "profiles#show",  as: :profile

    # App sections
    get "today",    to: "today#show",     as: :today
    get "plan",     to: "plan#show",      as: :plan
    get "discover", to: "discover#show",  as: :discover
    get "search",   to: "search#index",   as: :search

    # Onboarding / bulk photo ingest
    get  "onboarding",      to: "ingest#new",    as: :onboarding
    post "ingest/start",    to: "ingest#create", as: :ingest_start
    get  "ingest/:job_id",  to: "ingest#show",   as: :ingest_job

    # API endpoints (JSON only)
    namespace :api do
      post "tag_images", to: "tag_images#create"
      get  "health",     to: "health#show"
    end
  end
end
