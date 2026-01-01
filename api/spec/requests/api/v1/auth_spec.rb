require "rails_helper"

RSpec.describe "Api::V1::Auth", type: :request do
  let(:site) { create(:site, secret: "test-secret-123") }

  describe "POST /api/v1/auth/token" do
    let(:valid_params) { { site_id: site.name, secret: "test-secret-123" } }

    context "with valid credentials" do
      it "returns access and refresh tokens" do
        post "/api/v1/auth/token", params: valid_params

        expect(response).to have_http_status(:ok)
        json = json_response
        expect(json["data"]).to include(
          "access_token",
          "refresh_token",
          "token_type" => "Bearer"
        )
        expect(json["data"]["expires_in"]).to be_a(Integer)
      end

      it "returns valid JWT tokens" do
        post "/api/v1/auth/token", params: valid_params

        json = json_response
        access_payload = JwtService.decode_access_token(json["data"]["access_token"])
        expect(access_payload[:site_id]).to eq(site.id)
      end
    end

    context "with invalid credentials" do
      it "returns unauthorized for wrong secret" do
        post "/api/v1/auth/token", params: { site_id: site.name, secret: "wrong" }

        expect(response).to have_http_status(:unauthorized)
        json = json_response
        expect(json["errors"].first["detail"]).to eq("Invalid credentials")
      end

      it "returns unauthorized for non-existent site" do
        post "/api/v1/auth/token", params: { site_id: "fake-site", secret: "test" }

        expect(response).to have_http_status(:unauthorized)
      end
    end
  end

  describe "POST /api/v1/auth/refresh" do
    context "with valid refresh token" do
      it "returns new token pair" do
        tokens = JwtService.generate_token_pair(site: site)

        post "/api/v1/auth/refresh", params: { refresh_token: tokens[:refresh_token] }

        expect(response).to have_http_status(:ok)
        json = json_response
        expect(json["data"]).to include("access_token", "refresh_token")
      end
    end

    context "with invalid refresh token" do
      it "returns unauthorized for expired token" do
        payload = {
          site_id: site.id,
          type: "refresh",
          exp: 1.day.ago.to_i,
          iat: 2.days.ago.to_i
        }
        expired_token = JWT.encode(payload, Rails.application.secret_key_base, "HS256")

        post "/api/v1/auth/refresh", params: { refresh_token: expired_token }

        expect(response).to have_http_status(:unauthorized)
        expect(json_response["errors"].first["detail"]).to eq("Refresh token has expired")
      end

      it "returns bad request for missing token" do
        post "/api/v1/auth/refresh", params: {}

        expect(response).to have_http_status(:bad_request)
      end

      it "returns unauthorized for malformed token" do
        post "/api/v1/auth/refresh", params: { refresh_token: "invalid.token.here" }

        expect(response).to have_http_status(:unauthorized)
      end
    end
  end
end
