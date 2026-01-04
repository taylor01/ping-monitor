class Rack::Attack
  # Cache store for rate limiting (uses Rails.cache by default)
  # Rack::Attack.cache.store = ActiveSupport::Cache::MemoryStore.new

  ### Throttle Rules ###

  # Limit auth attempts by IP: 5 requests per 60 seconds
  throttle("auth/ip", limit: 5, period: 60.seconds) do |req|
    req.ip if req.path == "/api/v1/auth/token" && req.post?
  end

  # Limit auth attempts by identifier: 10 requests per 5 minutes
  # Prevents credential stuffing against specific accounts
  throttle("auth/identifier", limit: 10, period: 5.minutes) do |req|
    if req.path == "/api/v1/auth/token" && req.post?
      req.params["identifier"] || req.params["site_id"]
    end
  end

  # Limit refresh token attempts by IP: 10 requests per minute
  throttle("refresh/ip", limit: 10, period: 60.seconds) do |req|
    req.ip if req.path == "/api/v1/auth/refresh" && req.post?
  end

  ### Response Configuration ###

  # Return JSON error for throttled requests
  self.throttled_responder = lambda do |request|
    match_data = request.env["rack.attack.match_data"]
    now = match_data[:epoch_time]
    retry_after = match_data[:period] - (now % match_data[:period])

    [
      429,
      {
        "Content-Type" => "application/vnd.api+json",
        "Retry-After" => retry_after.to_s
      },
      [ {
        errors: [ {
          status: "429",
          title: "Too Many Requests",
          detail: "Rate limit exceeded. Retry after #{retry_after} seconds."
        } ]
      }.to_json ]
    ]
  end

  ### Safelist/Blocklist ###

  # Allow requests from localhost in development/test
  safelist("allow-localhost") do |req|
    req.ip == "127.0.0.1" || req.ip == "::1" if Rails.env.development? || Rails.env.test?
  end
end
