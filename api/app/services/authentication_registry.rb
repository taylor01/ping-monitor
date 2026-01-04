class AuthenticationRegistry
  STRATEGIES = {
    "site" => ->(identifier, secret) {
      site = Site.find_by(name: identifier)
      site if site&.authenticate_secret(secret)
    },
    "user" => ->(identifier, secret) {
      user = User.find_by(email: identifier)
      user if user&.authenticate(secret)
    },
    "agent" => ->(identifier, secret) {
      agent = Agent.find_by(name: identifier)
      agent if agent&.authenticate_secret(secret)
    },
    "api_client" => ->(identifier, secret) {
      client = ApiClient.find_by(client_id: identifier)
      client if client&.authenticate_secret(secret)
    }
  }.freeze

  class << self
    def authenticate(type:, identifier:, secret:)
      strategy = STRATEGIES[type.to_s.downcase]
      return nil unless strategy
      strategy.call(identifier, secret)
    end

    def supported_types
      STRATEGIES.keys
    end

    def supports?(type)
      STRATEGIES.key?(type.to_s.downcase)
    end
  end
end
