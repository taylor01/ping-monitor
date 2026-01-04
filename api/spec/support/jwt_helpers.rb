module JwtHelpers
  def auth_headers(authenticatable, scopes: nil)
    scopes ||= authenticatable.available_scopes
    token = JwtService.encode_access_token(authenticatable: authenticatable, scopes: scopes)
    { "Authorization" => "Bearer #{token}" }
  end

  # Backward compatible alias for tests that use site_auth_headers
  def site_auth_headers(site)
    auth_headers(site)
  end

  def agent_auth_headers(agent)
    auth_headers(agent)
  end

  def user_auth_headers(user)
    auth_headers(user)
  end

  def api_client_auth_headers(api_client)
    auth_headers(api_client)
  end

  def expired_auth_headers(authenticatable)
    payload = {
      authenticatable_type: authenticatable.class.name,
      authenticatable_id: authenticatable.id,
      scopes: [],
      type: "access",
      exp: 1.hour.ago.to_i,
      iat: 2.hours.ago.to_i
    }
    token = JWT.encode(payload, Rails.application.secret_key_base, "HS256")
    { "Authorization" => "Bearer #{token}" }
  end
end

RSpec.configure do |config|
  config.include JwtHelpers, type: :request
end
