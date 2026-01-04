require "rails_helper"

RSpec.describe JwtService do
  include ActiveSupport::Testing::TimeHelpers
  let(:site) { create(:site) }
  let(:user) { create(:user) }
  let(:agent) { create(:agent) }
  let(:api_client) { create(:api_client) }

  describe ".encode_access_token" do
    it "creates a valid JWT token" do
      token = described_class.encode_access_token(authenticatable: site, scopes: %w[sites:read])
      expect(token).to be_present
      expect(token.split(".").length).to eq(3)
    end

    it "includes required claims" do
      token = described_class.encode_access_token(authenticatable: site, scopes: %w[sites:read])
      payload = JWT.decode(token, Rails.application.secret_key_base, true, { algorithm: "HS256" }).first

      expect(payload["authenticatable_type"]).to eq("Site")
      expect(payload["authenticatable_id"]).to eq(site.id)
      expect(payload["scopes"]).to eq(%w[sites:read])
      expect(payload["type"]).to eq("access")
      expect(payload["exp"]).to be_present
      expect(payload["iat"]).to be_present
    end

    it "sets correct expiration time" do
      freeze_time do
        token = described_class.encode_access_token(authenticatable: site, scopes: [])
        payload = JWT.decode(token, Rails.application.secret_key_base, true, { algorithm: "HS256" }).first

        expect(payload["exp"]).to eq(1.hour.from_now.to_i)
      end
    end
  end

  describe ".encode_refresh_token" do
    it "creates a valid JWT token" do
      token = described_class.encode_refresh_token(authenticatable: site)
      expect(token).to be_present
      expect(token.split(".").length).to eq(3)
    end

    it "includes required claims" do
      token = described_class.encode_refresh_token(authenticatable: site)
      payload = JWT.decode(token, Rails.application.secret_key_base, true, { algorithm: "HS256" }).first

      expect(payload["authenticatable_type"]).to eq("Site")
      expect(payload["authenticatable_id"]).to eq(site.id)
      expect(payload["type"]).to eq("refresh")
      expect(payload["exp"]).to be_present
    end

    it "sets correct expiration time (30 days)" do
      freeze_time do
        token = described_class.encode_refresh_token(authenticatable: site)
        payload = JWT.decode(token, Rails.application.secret_key_base, true, { algorithm: "HS256" }).first

        expect(payload["exp"]).to eq(30.days.from_now.to_i)
      end
    end
  end

  describe ".decode" do
    context "with valid token" do
      it "decodes access token successfully" do
        token = described_class.encode_access_token(authenticatable: site, scopes: %w[sites:read])
        payload = described_class.decode(token)

        expect(payload[:authenticatable_type]).to eq("Site")
        expect(payload[:authenticatable_id]).to eq(site.id)
        expect(payload[:scopes]).to eq(%w[sites:read])
      end

      it "decodes refresh token successfully" do
        token = described_class.encode_refresh_token(authenticatable: user)
        payload = described_class.decode(token)

        expect(payload[:authenticatable_type]).to eq("User")
        expect(payload[:authenticatable_id]).to eq(user.id)
      end
    end

    context "with expired token" do
      it "raises TokenExpiredError" do
        token = described_class.encode_access_token(authenticatable: site, scopes: [])

        travel_to 2.hours.from_now do
          expect { described_class.decode(token) }.to raise_error(JwtService::TokenExpiredError)
        end
      end
    end

    context "with invalid token" do
      it "raises InvalidTokenError for malformed token" do
        expect { described_class.decode("invalid.token.here") }.to raise_error(JwtService::InvalidTokenError)
      end

      it "raises InvalidTokenError for token signed with wrong key" do
        token = JWT.encode({ sub: "test" }, "wrong-secret", "HS256")
        expect { described_class.decode(token) }.to raise_error(JwtService::InvalidTokenError)
      end
    end

    context "with key rotation" do
      let(:previous_secret) { "previous-secret-key-for-testing" }

      before do
        allow(ENV).to receive(:[]).and_call_original
        allow(ENV).to receive(:[]).with("JWT_SECRET_KEY_PREVIOUS").and_return(previous_secret)
      end

      it "decodes token signed with current key" do
        token = described_class.encode_access_token(authenticatable: site, scopes: [])
        payload = described_class.decode(token)

        expect(payload[:authenticatable_type]).to eq("Site")
      end

      it "decodes token signed with previous key" do
        # Simulate token created with previous key
        old_token = JWT.encode(
          {
            authenticatable_type: "Site",
            authenticatable_id: site.id,
            type: "access",
            exp: 1.hour.from_now.to_i,
            iat: Time.current.to_i
          },
          previous_secret,
          "HS256"
        )

        payload = described_class.decode(old_token)
        expect(payload[:authenticatable_type]).to eq("Site")
        expect(payload[:authenticatable_id]).to eq(site.id)
      end

      it "fails for token signed with unknown key" do
        bad_token = JWT.encode({ sub: "test" }, "unknown-key", "HS256")
        expect { described_class.decode(bad_token) }.to raise_error(JwtService::InvalidTokenError)
      end

      it "raises TokenExpiredError even for previous key tokens" do
        old_token = JWT.encode(
          {
            authenticatable_type: "Site",
            authenticatable_id: site.id,
            type: "access",
            exp: 1.hour.ago.to_i,
            iat: 2.hours.ago.to_i
          },
          previous_secret,
          "HS256"
        )

        expect { described_class.decode(old_token) }.to raise_error(JwtService::TokenExpiredError)
      end
    end

    context "backward compatibility with legacy site_id format" do
      it "normalizes old site_id format to new format" do
        legacy_token = JWT.encode(
          {
            site_id: site.id,
            type: "access",
            exp: 1.hour.from_now.to_i,
            iat: Time.current.to_i
          },
          Rails.application.secret_key_base,
          "HS256"
        )

        payload = described_class.decode(legacy_token)

        expect(payload[:authenticatable_type]).to eq("Site")
        expect(payload[:authenticatable_id]).to eq(site.id)
        expect(payload[:scopes]).to eq(Site.new.available_scopes)
      end
    end
  end

  describe ".decode_access_token" do
    it "accepts access tokens" do
      token = described_class.encode_access_token(authenticatable: site, scopes: [])
      payload = described_class.decode_access_token(token)

      expect(payload[:type]).to eq("access")
    end

    it "rejects refresh tokens" do
      token = described_class.encode_refresh_token(authenticatable: site)

      expect { described_class.decode_access_token(token) }
        .to raise_error(JwtService::InvalidTokenError, "Not an access token")
    end
  end

  describe ".decode_refresh_token" do
    it "accepts refresh tokens" do
      token = described_class.encode_refresh_token(authenticatable: site)
      payload = described_class.decode_refresh_token(token)

      expect(payload[:type]).to eq("refresh")
    end

    it "rejects access tokens" do
      token = described_class.encode_access_token(authenticatable: site, scopes: [])

      expect { described_class.decode_refresh_token(token) }
        .to raise_error(JwtService::InvalidTokenError, "Not a refresh token")
    end
  end

  describe ".generate_token_pair" do
    it "returns both access and refresh tokens" do
      result = described_class.generate_token_pair(authenticatable: site)

      expect(result[:access_token]).to be_present
      expect(result[:refresh_token]).to be_present
      expect(result[:token_type]).to eq("Bearer")
      expect(result[:expires_in]).to eq(1.hour.to_i)
    end

    it "uses model's available_scopes when scopes not specified" do
      result = described_class.generate_token_pair(authenticatable: site)

      expect(result[:scopes]).to eq(site.available_scopes)
    end

    it "uses provided scopes when specified" do
      result = described_class.generate_token_pair(
        authenticatable: site,
        scopes: %w[sites:read]
      )

      expect(result[:scopes]).to eq(%w[sites:read])
    end

    it "works with all authenticatable types" do
      [ site, user, agent, api_client ].each do |authenticatable|
        result = described_class.generate_token_pair(authenticatable: authenticatable)

        expect(result[:access_token]).to be_present
        expect(result[:refresh_token]).to be_present
      end
    end
  end

  describe ".find_authenticatable" do
    it "finds Site from payload" do
      payload = { authenticatable_type: "Site", authenticatable_id: site.id }
      result = described_class.find_authenticatable(payload)

      expect(result).to eq(site)
    end

    it "finds User from payload" do
      payload = { authenticatable_type: "User", authenticatable_id: user.id }
      result = described_class.find_authenticatable(payload)

      expect(result).to eq(user)
    end

    it "finds Agent from payload" do
      payload = { authenticatable_type: "Agent", authenticatable_id: agent.id }
      result = described_class.find_authenticatable(payload)

      expect(result).to eq(agent)
    end

    it "finds ApiClient from payload" do
      payload = { authenticatable_type: "ApiClient", authenticatable_id: api_client.id }
      result = described_class.find_authenticatable(payload)

      expect(result).to eq(api_client)
    end

    it "raises InvalidTokenError for missing type" do
      payload = { authenticatable_id: site.id }

      expect { described_class.find_authenticatable(payload) }
        .to raise_error(JwtService::InvalidTokenError, "Missing authenticatable type")
    end

    it "raises InvalidTokenError for invalid type" do
      payload = { authenticatable_type: "InvalidType", authenticatable_id: 1 }

      expect { described_class.find_authenticatable(payload) }
        .to raise_error(JwtService::InvalidTokenError, /Invalid authenticatable type/)
    end

    it "raises RecordNotFound for non-existent record" do
      payload = { authenticatable_type: "Site", authenticatable_id: 99999 }

      expect { described_class.find_authenticatable(payload) }
        .to raise_error(ActiveRecord::RecordNotFound)
    end
  end
end
