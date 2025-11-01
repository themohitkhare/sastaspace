Rails.application.routes.draw do
  resources :outfits do
    collection do
      get :builder
      get :inspiration
      get :new_from_photo
    end
  end
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "up#show", as: :rails_health_check

  # Health and readiness checks
  get "health" => "health#show"
  get "ready" => "ready#show"

  # Root route
  root "inventory_items#index"

  # Authentication routes
  get "login", to: "sessions#new"
  post "login", to: "sessions#create"
  delete "logout", to: "sessions#destroy"
  get "register", to: "registrations#new"
  post "register", to: "registrations#create"

  # Frontend routes
  resources :inventory_items do
    collection do
      delete :bulk_delete
      get :new_ai
    end
  end

  # RubyLLM Chat demo routes
  resources :chats, only: [ :index, :show, :new, :create ] do
    member do
      post :stream
    end
  end

  # API routes
  namespace :api do
    namespace :v1 do
      # Health check
      get "health" => "health#show"

      # Authentication
      post "auth/register" => "auth#register"
      post "auth/login" => "auth#login"
      post "auth/refresh" => "auth#refresh"
      get "auth/me" => "auth#me"
      post "auth/logout" => "auth#logout"
      post "auth/logout_all" => "auth#logout_all"

      # Categories
      resources :categories, only: [ :index, :show ] do
        collection do
          get :tree      # Full hierarchical tree
          get :roots     # Root categories only
        end

        member do
          get :children  # Direct children
          get :inventory_items  # Items in this category
        end
      end

      # Inventory items
      resources :inventory_items do
        member do
          patch :worn
          get :similar
          post :primary_image, action: :attach_primary_image
          post :additional_images, action: :attach_additional_images
          delete :primary_image, action: :detach_primary_image
          delete "additional_images/:image_id", action: :detach_additional_image
        end
        collection do
          get :search
          post :semantic_search
          post :analyze_image_for_creation
          get "analyze_image_status/:job_id", action: :analyze_image_status
          post :batch_create
        end
      end

      # AI Analysis
      post "ai/analyze" => "ai_analysis#analyze_image"
      get "ai/analysis/:id" => "ai_analysis#get_analysis"
      get "ai/analyses" => "ai_analysis#index"
      post "inventory_items/:id/analyze" => "ai_analysis#analyze_image"
      get "inventory_items/:id/analysis" => "ai_analysis#get_analysis"
      delete "inventory_items/:id/analysis" => "ai_analysis#destroy"

      # Outfits
      resources :outfits do
        collection do
          get :color_analysis
          post :analyze_photo
          get "analyze_photo_status/:job_id", action: :analyze_photo_status
        end
        member do
          post :duplicate
          put :toggle_favorite
          post :inventory_items
          delete "inventory_items/:inventory_item_id" => :remove_inventory_item
        end
      end

      # Users
      scope :users do
        post "export" => "users#export"
        get "export/status" => "users#export_status"
        get "export/download" => "users#download_export"
        delete "delete" => "users#delete"
      end

      # API Documentation
      get "docs" => "docs#show"
      get "docs/openapi" => "docs#openapi"
      resources :outfits do
        member do
          patch :wear
          patch :favorite
          get :suggestions
          post :duplicate
        end
      end
    end
  end

  # Render dynamic PWA files from app/views/pwa/* (remember to link manifest in application.html.erb)
  # get "manifest" => "rails/pwa#manifest", as: :pwa_manifest
  # get "service-worker" => "rails/pwa#service_worker", as: :pwa_service_worker

  # Defines the root path route ("/")
  # root "posts#index"
end
