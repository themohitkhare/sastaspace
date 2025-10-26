Rails.application.routes.draw do
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "up#show", as: :rails_health_check

  # Health and readiness checks
  get "health" => "health#show"
  get "ready" => "ready#show"

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
    end
  end

  # Render dynamic PWA files from app/views/pwa/* (remember to link manifest in application.html.erb)
  # get "manifest" => "rails/pwa#manifest", as: :pwa_manifest
  # get "service-worker" => "rails/pwa#service_worker", as: :pwa_service_worker

  # Defines the root path route ("/")
  # root "posts#index"
end
