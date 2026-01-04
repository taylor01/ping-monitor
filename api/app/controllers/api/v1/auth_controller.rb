module Api
  module V1
    class AuthController < ApplicationController
      skip_before_action :verify_authenticity_token, raise: false

      # POST /api/v1/auth/token
      # Authenticate with credentials and get tokens
      # Supports: sites, users, agents, api_clients
      def create
        authenticatable = find_and_authenticate

        unless authenticatable
          log_auth_event("authentication_failure", identifier: params[:identifier] || params[:site_id])
          return render_error("Invalid credentials", status: :unauthorized)
        end

        unless authenticatable.can_authenticate?
          log_auth_event("authentication_inactive", authenticatable: authenticatable)
          return render_error("Account is not active", status: :forbidden)
        end

        scopes = requested_scopes(authenticatable)
        tokens = JwtService.generate_token_pair(
          authenticatable: authenticatable,
          scopes: scopes
        )

        log_auth_event("authentication_success", authenticatable: authenticatable)
        render json: { data: tokens }, status: :ok
      end

      # POST /api/v1/auth/refresh
      # Refresh access token using refresh token
      def refresh
        refresh_token = params[:refresh_token]

        if refresh_token.blank?
          return render_error("Missing refresh token", status: :bad_request)
        end

        payload = JwtService.decode_refresh_token(refresh_token)
        authenticatable = JwtService.find_authenticatable(payload)

        unless authenticatable.can_authenticate?
          return render_error("Account is not active", status: :forbidden)
        end

        # Revalidate scopes against current permissions
        # This ensures role/permission changes are reflected on refresh
        old_scopes = payload[:scopes] || []
        new_scopes = authenticatable.validate_scopes(old_scopes)

        tokens = JwtService.generate_token_pair(
          authenticatable: authenticatable,
          scopes: new_scopes.presence
        )

        render json: { data: tokens }, status: :ok
      rescue ActiveRecord::RecordNotFound
        render_error("Account not found", status: :unauthorized)
      rescue JwtService::TokenExpiredError
        render_error("Refresh token has expired", status: :unauthorized)
      rescue JwtService::InvalidTokenError => e
        render_error(e.message, status: :unauthorized)
      end

      private

      def find_and_authenticate
        type = (params[:authenticatable_type] || "site").downcase
        identifier = params[:identifier] || params[:site_id]
        secret = params[:secret]

        AuthenticationRegistry.authenticate(
          type: type,
          identifier: identifier,
          secret: secret
        )
      end

      def requested_scopes(authenticatable)
        authenticatable.validate_scopes(params[:scopes])
      end

      def render_error(message, status:)
        render json: {
          errors: [ {
            status: Rack::Utils.status_code(status).to_s,
            title: status.to_s.titleize,
            detail: message
          } ]
        }, status: status
      end

      def log_auth_event(event, authenticatable: nil, identifier: nil)
        Rails.logger.info({
          event: event,
          authenticatable_type: authenticatable&.class&.name,
          authenticatable_id: authenticatable&.id,
          identifier: identifier&.to_s&.truncate(100)&.gsub(/[\r\n]/, ""),
          ip: request.remote_ip,
          user_agent: request.user_agent&.truncate(200)&.gsub(/[\r\n]/, "")
        }.compact.to_json)
      end
    end
  end
end
