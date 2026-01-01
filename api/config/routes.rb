Rails.application.routes.draw do
  # Health check for load balancers
  get "up" => "rails/health#show", as: :rails_health_check

  namespace :api do
    namespace :v1 do
      # Authentication (no auth required)
      post "auth/token", to: "auth#create"
      post "auth/refresh", to: "auth#refresh"

      # Sites
      get "sites/me", to: "sites#me"
      resources :sites, only: [:index, :show]

      # Measurements
      resources :measurements, only: [:index, :create]

      # Anomalies
      resources :anomalies, only: [:index, :show] do
        member do
          patch :resolve
        end
      end
    end
  end
end
