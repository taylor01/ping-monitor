require "rails_helper"

RSpec.describe "Rate Limiting", type: :request do
  # Note: Rate limiting is safelisted for localhost in test environment
  # These tests verify the configuration is correct

  describe "rack-attack configuration" do
    it "loads rack-attack initializer" do
      expect(Rack::Attack).to be_present
    end

    it "has auth/ip throttle configured" do
      throttle = Rack::Attack.throttles["auth/ip"]
      expect(throttle).to be_present
    end

    it "has auth/identifier throttle configured" do
      throttle = Rack::Attack.throttles["auth/identifier"]
      expect(throttle).to be_present
    end

    it "has refresh/ip throttle configured" do
      throttle = Rack::Attack.throttles["refresh/ip"]
      expect(throttle).to be_present
    end
  end

  describe "throttle rules" do
    describe "auth/ip throttle" do
      it "matches auth token endpoint" do
        throttle = Rack::Attack.throttles["auth/ip"]
        request = double(
          ip: "192.168.1.1",
          path: "/api/v1/auth/token",
          post?: true
        )

        discriminator = throttle.block.call(request)
        expect(discriminator).to eq("192.168.1.1")
      end

      it "does not match other endpoints" do
        throttle = Rack::Attack.throttles["auth/ip"]
        request = double(
          ip: "192.168.1.1",
          path: "/api/v1/sites",
          post?: false
        )

        discriminator = throttle.block.call(request)
        expect(discriminator).to be_nil
      end
    end

    describe "auth/identifier throttle" do
      it "matches auth token endpoint with identifier param" do
        throttle = Rack::Attack.throttles["auth/identifier"]
        request = double(
          path: "/api/v1/auth/token",
          post?: true,
          params: { "identifier" => "test@example.com" }
        )

        discriminator = throttle.block.call(request)
        expect(discriminator).to eq("test@example.com")
      end

      it "matches auth token endpoint with site_id param (legacy)" do
        throttle = Rack::Attack.throttles["auth/identifier"]
        request = double(
          path: "/api/v1/auth/token",
          post?: true,
          params: { "site_id" => "my-site" }
        )

        discriminator = throttle.block.call(request)
        expect(discriminator).to eq("my-site")
      end
    end

    describe "refresh/ip throttle" do
      it "matches refresh endpoint" do
        throttle = Rack::Attack.throttles["refresh/ip"]
        request = double(
          ip: "192.168.1.1",
          path: "/api/v1/auth/refresh",
          post?: true
        )

        discriminator = throttle.block.call(request)
        expect(discriminator).to eq("192.168.1.1")
      end
    end
  end

  describe "throttled response format" do
    it "returns JSON:API formatted error" do
      # Create a mock throttled request
      env = {
        "rack.attack.match_data" => {
          epoch_time: Time.now.to_i,
          period: 60
        }
      }
      mock_request = double(env: env)

      response = Rack::Attack.throttled_responder.call(mock_request)

      expect(response[0]).to eq(429)
      expect(response[1]["Content-Type"]).to eq("application/vnd.api+json")
      expect(response[1]["Retry-After"]).to be_present

      body = JSON.parse(response[2].first)
      expect(body["errors"]).to be_present
      expect(body["errors"].first["status"]).to eq("429")
      expect(body["errors"].first["title"]).to eq("Too Many Requests")
    end
  end

  describe "safelist" do
    it "safelists localhost in development/test" do
      safelist = Rack::Attack.safelists["allow-localhost"]
      expect(safelist).to be_present

      # Test that localhost is safelisted
      request = double(ip: "127.0.0.1")
      result = safelist.block.call(request)
      expect(result).to be true
    end

    it "safelists IPv6 localhost in development/test" do
      safelist = Rack::Attack.safelists["allow-localhost"]

      request = double(ip: "::1")
      result = safelist.block.call(request)
      expect(result).to be true
    end
  end
end
