class JwtService
  ALGORITHM = "HS256"
  ACCESS_TOKEN_EXPIRY = 1.hour
  REFRESH_TOKEN_EXPIRY = 30.days

  class << self
    def encode_access_token(authenticatable:, scopes: [])
      payload = {
        sub: "#{authenticatable.class.name.downcase}:#{authenticatable.id}",
        authenticatable_type: authenticatable.class.name,
        authenticatable_id: authenticatable.id,
        scopes: scopes,
        type: "access",
        exp: ACCESS_TOKEN_EXPIRY.from_now.to_i,
        iat: Time.current.to_i
      }
      JWT.encode(payload, secret_key, ALGORITHM)
    end

    def encode_refresh_token(authenticatable:)
      payload = {
        sub: "#{authenticatable.class.name.downcase}:#{authenticatable.id}",
        authenticatable_type: authenticatable.class.name,
        authenticatable_id: authenticatable.id,
        type: "refresh",
        exp: REFRESH_TOKEN_EXPIRY.from_now.to_i,
        iat: Time.current.to_i
      }
      JWT.encode(payload, secret_key, ALGORITHM)
    end

    def decode(token)
      payload = nil
      last_error = nil

      # Validate token structure before attempting decode
      raise InvalidTokenError unless token.to_s.count(".") == 2

      # Try each secret key (supports key rotation)
      # Use algorithms array to prevent algorithm confusion attacks
      secret_keys.each do |key|
        decoded = JWT.decode(token, key, true, { algorithms: [ ALGORITHM ] })
        payload = decoded.first.with_indifferent_access
        break
      rescue JWT::ExpiredSignature
        raise TokenExpiredError
      rescue JWT::DecodeError => e
        last_error = e
        next
      end

      raise InvalidTokenError if payload.nil?

      # Backward compatibility: normalize old site_id format to new format
      if payload[:site_id] && !payload[:authenticatable_type]
        payload[:authenticatable_type] = "Site"
        payload[:authenticatable_id] = payload[:site_id]
        # Use Site's default scopes for legacy tokens
        payload[:scopes] ||= Site.new.available_scopes
        Rails.logger.warn("Deprecated token format detected (site_id only). Please upgrade to new token format.")
      end

      payload
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

    def generate_token_pair(authenticatable:, scopes: nil)
      # Delegate scope resolution to the model
      scopes = scopes.presence || authenticatable.available_scopes
      {
        access_token: encode_access_token(authenticatable: authenticatable, scopes: scopes),
        refresh_token: encode_refresh_token(authenticatable: authenticatable),
        token_type: "Bearer",
        expires_in: ACCESS_TOKEN_EXPIRY.to_i,
        scopes: scopes
      }
    end

    def find_authenticatable(payload)
      type = payload[:authenticatable_type]
      id = payload[:authenticatable_id]

      raise InvalidTokenError, "Missing authenticatable type" if type.blank?

      # Use explicit case statement instead of constantize to prevent RCE
      klass = case type
      when "Site" then Site
      when "User" then User
      when "Agent" then Agent
      when "ApiClient" then ApiClient
      else raise InvalidTokenError, "Invalid authenticatable type: #{type}"
      end

      klass.find(id)
    end

    private

    # Primary key for encoding new tokens
    def secret_key
      secret_keys.first
    end

    # All valid keys for decoding (supports rotation)
    # Set JWT_SECRET_KEY env var for production (recommended)
    # Set JWT_SECRET_KEY_PREVIOUS env var during rotation period
    def secret_keys
      primary = ENV["JWT_SECRET_KEY"].presence || Rails.application.secret_key_base
      previous = ENV["JWT_SECRET_KEY_PREVIOUS"]

      if ENV["JWT_SECRET_KEY"].blank? && Rails.env.production?
        Rails.logger.warn("JWT_SECRET_KEY not set - using secret_key_base. " \
                         "Consider setting a dedicated JWT secret for production.")
      end

      [ primary, previous ].compact
    end
  end

  # Custom errors
  class TokenExpiredError < StandardError; end
  class InvalidTokenError < StandardError; end
end
