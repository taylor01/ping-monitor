Rails.application.routes.draw do
  # Health check for load balancers
  get "up" => "rails/health#show", as: :rails_health_check

  # Health check for NC (no auth required)
  get "health", to: "health#show"

  namespace :api do
    namespace :v1 do
      # Authentication (no auth required)
      post "auth/token", to: "auth#create"
      post "auth/refresh", to: "auth#refresh"

      # Sites
      get "sites/me", to: "sites#me"
      resources :sites, only: [ :index, :show ] do
        member do
          get :status
        end
      end

      # Measurements
      resources :measurements, only: [ :index, :create ]

      # Anomalies
      resources :anomalies, only: [ :index, :show ] do
        collection do
          get :history
        end
        member do
          patch :resolve
        end
      end

      # Baselines
      resources :baselines, only: [ :index, :show ], param: :host
    end
  end
end
