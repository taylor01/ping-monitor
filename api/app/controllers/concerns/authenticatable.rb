module Authenticatable
  extend ActiveSupport::Concern

  included do
    before_action :authenticate_request!
    attr_reader :current_authenticatable, :current_scopes
  end

  # Convenience accessors for specific types
  def current_site
    current_authenticatable if current_authenticatable.is_a?(Site)
  end

  def current_user
    current_authenticatable if current_authenticatable.is_a?(User)
  end

  def current_agent
    current_authenticatable if current_authenticatable.is_a?(Agent)
  end

  def current_api_client
    current_authenticatable if current_authenticatable.is_a?(ApiClient)
  end

  # Scope-based authorization helpers
  def has_scope?(scope)
    return true if current_scopes&.include?("*")
    current_scopes&.include?(scope.to_s)
  end

  def require_scope!(scope)
    unless has_scope?(scope)
      render_forbidden("Missing required scope: #{scope}")
    end
  end

  # Policy-based authorization helpers
  def authorize(record, query = nil)
    query ||= "#{action_name}?"
    policy_instance = policy(record)

    if policy_instance.public_send(query)
      true
    else
      render_forbidden("Not authorized to #{query.to_s.chomp('?')} this #{record.class.name.downcase}")
      nil
    end
  end

  def policy(record)
    klass = record.is_a?(Class) ? record : record.class
    "#{klass.name}Policy".constantize.new(current_authenticatable, record)
  end

  def policy_scope(scope)
    klass = scope.is_a?(Class) ? scope : scope.model
    "#{klass.name}Policy::Scope".constantize.new(current_authenticatable, scope).resolve
  end

  private

  def authenticate_request!
    token = extract_token_from_header
    raise JwtService::InvalidTokenError, "Missing authorization header" if token.blank?

    payload = JwtService.decode_access_token(token)
    @current_authenticatable = JwtService.find_authenticatable(payload)
    @current_scopes = payload[:scopes] || []
  rescue ActiveRecord::RecordNotFound
    render_unauthorized("Account not found")
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

  def render_forbidden(message = "Forbidden")
    render json: {
      errors: [ {
        status: "403",
        title: "Forbidden",
        detail: message
      } ]
    }, status: :forbidden
  end
end
