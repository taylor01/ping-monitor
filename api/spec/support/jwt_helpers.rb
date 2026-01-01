module JwtHelpers
  def auth_headers(site)
    token = JwtService.encode_access_token(site_id: site.id)
    { "Authorization" => "Bearer #{token}" }
  end

  def expired_auth_headers(site)
    payload = {
      site_id: site.id,
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
