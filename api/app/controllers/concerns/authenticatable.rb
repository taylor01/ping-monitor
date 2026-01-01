module Authenticatable
  extend ActiveSupport::Concern

  included do
    before_action :authenticate_request!
    attr_reader :current_site
  end

  private

  def authenticate_request!
    token = extract_token_from_header
    raise JwtService::InvalidTokenError, "Missing authorization header" if token.blank?

    payload = JwtService.decode_access_token(token)
    @current_site = Site.find(payload[:site_id])
  rescue ActiveRecord::RecordNotFound
    render_unauthorized("Site not found")
  rescue JwtService::TokenExpiredError
    render_unauthorized("Token has expired")
  rescue JwtService::InvalidTokenError => e
    render_unauthorized(e.message)
  end

  def extract_token_from_header
    header = request.headers["Authorization"]
    return nil unless header.present?

    header.split(" ").last
  end

  def render_unauthorized(message = "Unauthorized")
    render json: {
      errors: [ {
        status: "401",
        title: "Unauthorized",
        detail: message
      } ]
    }, status: :unauthorized
  end
end
