Rails.application.routes.draw do
  mount MaintenanceTasks::Engine, at: "/maintenance_tasks"
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

  # Root route - Landing page for public, inventory for logged-in users
  root "pages#home"

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

  # Sidekiq Web UI (admin only)
  # See https://github.com/sidekiq/sidekiq/wiki/Monitoring for documentation
  require "sidekiq/web"
  require "admin_constraint"
  mount Sidekiq::Web => "/admin/jobs", constraints: AdminConstraint.new

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


      # Clothing Detection
      post "clothing_detection/analyze" => "clothing_detection#analyze"
      get "clothing_detection/status/:job_id" => "clothing_detection#status"
      get "clothing_detection/analysis/:id" => "clothing_detection#show"
      get "clothing_detection/analyses" => "clothing_detection#index"

      # Stock Photo Extraction
      resource :stock_extraction, only: [], controller: "stock_extraction" do
        post :extract
        get "status/:job_id", to: "stock_extraction#status", as: :status
      end

      # Outfits
      resources :outfits do
        collection do
          get :color_analysis
          post :analyze_photo
          get "analyze_photo_status/:job_id", action: :analyze_photo_status
        end
        member do
          patch :wear
          patch :favorite
          get :suggestions
          get :completeness
          post :duplicate
          put :toggle_favorite
          post :inventory_items
          delete "inventory_items/:inventory_item_id" => :remove_inventory_item
        end
        resources :outfit_items, only: [ :create, :destroy ] do
          member do
            patch :update_styling_notes
          end
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
