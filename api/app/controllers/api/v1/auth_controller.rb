module Api
  module V1
    class AuthController < ApplicationController
      skip_before_action :verify_authenticity_token, raise: false

      # POST /api/v1/auth/token
      # Authenticate with site credentials and get tokens
      def create
        site = Site.find_by(name: params[:site_id])

        if site&.authenticate_secret(params[:secret])
          tokens = JwtService.generate_token_pair(site: site)
          render json: { data: tokens }, status: :ok
        else
          render_error("Invalid credentials", status: :unauthorized)
        end
      end

      # POST /api/v1/auth/refresh
      # Refresh access token using refresh token
      def refresh
        refresh_token = params[:refresh_token]

        if refresh_token.blank?
          return render_error("Missing refresh token", status: :bad_request)
        end

        payload = JwtService.decode_refresh_token(refresh_token)
        site = Site.find(payload[:site_id])

        tokens = JwtService.generate_token_pair(site: site)
        render json: { data: tokens }, status: :ok
      rescue ActiveRecord::RecordNotFound
        render_error("Site not found", status: :unauthorized)
      rescue JwtService::TokenExpiredError
        render_error("Refresh token has expired", status: :unauthorized)
      rescue JwtService::InvalidTokenError => e
        render_error(e.message, status: :unauthorized)
      end

      private

      def render_error(message, status:)
        render json: {
          errors: [{
            status: Rack::Utils.status_code(status).to_s,
            title: status.to_s.titleize,
            detail: message
          }]
        }, status: status
      end
    end
  end
end
