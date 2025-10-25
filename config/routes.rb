Rails.application.routes.draw do
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "up#show", as: :rails_health_check

  # Health and readiness checks
  get "health" => "health#show"
  get "ready" => "ready#show"

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

      # Clothing items
      resources :clothing_items do
        member do
          post :photo
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
          delete 'additional_images/:image_id', action: :detach_additional_image
        end
        collection do
          get :search
        end
      end

      # AI Analysis
      post "ai/analyze" => "ai_analysis#analyze_image"
      get "ai/analysis/:id" => "ai_analysis#get_analysis"
      get "ai/analyses" => "ai_analysis#index"
      post "clothing_items/:id/analyze" => "ai_analysis#analyze_image"
      get "clothing_items/:id/analysis" => "ai_analysis#get_analysis"
      delete "clothing_items/:id/analysis" => "ai_analysis#destroy"

      # Outfits
      resources :outfits do
        member do
          post :duplicate
          put :toggle_favorite
          post :clothing_items
          delete "clothing_items/:clothing_item_id" => :remove_clothing_item
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
