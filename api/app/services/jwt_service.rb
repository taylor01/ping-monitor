class JwtService
  ALGORITHM = "HS256"
  ACCESS_TOKEN_EXPIRY = 1.hour
  REFRESH_TOKEN_EXPIRY = 30.days

  class << self
    def encode_access_token(site_id:)
      payload = {
        site_id: site_id,
        type: "access",
        exp: ACCESS_TOKEN_EXPIRY.from_now.to_i,
        iat: Time.current.to_i
      }
      JWT.encode(payload, secret_key, ALGORITHM)
    end

    def encode_refresh_token(site_id:)
      payload = {
        site_id: site_id,
        type: "refresh",
        exp: REFRESH_TOKEN_EXPIRY.from_now.to_i,
        iat: Time.current.to_i
      }
      JWT.encode(payload, secret_key, ALGORITHM)
    end

    def decode(token)
      decoded = JWT.decode(token, secret_key, true, { algorithm: ALGORITHM })
      decoded.first.with_indifferent_access
    rescue JWT::ExpiredSignature
      raise TokenExpiredError
    rescue JWT::DecodeError
      raise InvalidTokenError
    end

    def decode_access_token(token)
      payload = decode(token)
      raise InvalidTokenError, "Not an access token" unless payload[:type] == "access"

      payload
    end

    def decode_refresh_token(token)
      payload = decode(token)
      raise InvalidTokenError, "Not a refresh token" unless payload[:type] == "refresh"

      payload
    end

    def generate_token_pair(site:)
      {
        access_token: encode_access_token(site_id: site.id),
        refresh_token: encode_refresh_token(site_id: site.id),
        token_type: "Bearer",
        expires_in: ACCESS_TOKEN_EXPIRY.to_i
      }
    end

    private

    def secret_key
      Rails.application.secret_key_base
    end
  end

  # Custom errors
  class TokenExpiredError < StandardError; end
  class InvalidTokenError < StandardError; end
end
