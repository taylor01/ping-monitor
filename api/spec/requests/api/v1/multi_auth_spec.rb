require "rails_helper"

RSpec.describe "Multi-Authenticatable Authorization", type: :request do
  let(:site) { create(:site) }
  let(:other_site) { create(:site) }
  let(:user_viewer) { create(:user, role: :viewer) }
  let(:user_operator) { create(:user, role: :operator) }
  let(:user_admin) { create(:user, role: :admin) }
  let(:agent) { create(:agent) }
  let(:api_client) { create(:api_client, allowed_scopes: %w[sites:read anomalies:read]) }

  describe "GET /api/v1/sites" do
    before do
      site
      other_site
    end

    it "allows Site authentication" do
      get "/api/v1/sites", headers: auth_headers(site)
      expect(response).to have_http_status(:ok)
    end

    it "allows User authentication" do
      get "/api/v1/sites", headers: auth_headers(user_viewer)
      expect(response).to have_http_status(:ok)
    end

    it "allows Agent authentication" do
      get "/api/v1/sites", headers: auth_headers(agent)
      expect(response).to have_http_status(:ok)
    end

    it "allows ApiClient authentication" do
      get "/api/v1/sites", headers: auth_headers(api_client)
      expect(response).to have_http_status(:ok)
    end
  end

  describe "GET /api/v1/sites/me" do
    it "allows Site authentication" do
      get "/api/v1/sites/me", headers: auth_headers(site)
      expect(response).to have_http_status(:ok)
    end

    it "denies User authentication" do
      get "/api/v1/sites/me", headers: auth_headers(user_viewer)
      expect(response).to have_http_status(:forbidden)
    end

    it "denies Agent authentication" do
      get "/api/v1/sites/me", headers: auth_headers(agent)
      expect(response).to have_http_status(:forbidden)
    end

    it "denies ApiClient authentication" do
      get "/api/v1/sites/me", headers: auth_headers(api_client)
      expect(response).to have_http_status(:forbidden)
    end
  end

  describe "GET /api/v1/measurements" do
    let!(:site_measurement) { create(:measurement, site: site) }
    let!(:other_measurement) { create(:measurement, site: other_site) }

    context "when authenticated as Site" do
      it "returns only own measurements" do
        get "/api/v1/measurements", headers: auth_headers(site)
        expect(response).to have_http_status(:ok)

        data = JSON.parse(response.body)["data"]
        expect(data.length).to eq(1)
        expect(data.first["id"]).to eq(site_measurement.id.to_s)
      end
    end

    context "when authenticated as User" do
      it "returns all measurements" do
        get "/api/v1/measurements", headers: auth_headers(user_viewer)
        expect(response).to have_http_status(:ok)

        data = JSON.parse(response.body)["data"]
        expect(data.length).to eq(2)
      end
    end

    context "when authenticated as Agent" do
      it "returns all measurements" do
        get "/api/v1/measurements", headers: auth_headers(agent)
        expect(response).to have_http_status(:ok)

        data = JSON.parse(response.body)["data"]
        expect(data.length).to eq(2)
      end
    end
  end

  describe "POST /api/v1/measurements" do
    let(:measurement_params) do
      {
        data: {
          type: "measurement_batch",
          attributes: {
            site: site.name,
            timestamp: Time.current.iso8601,
            measurements: [
              { host: "router.local", ip: "192.168.1.1", latency_ms: 5.2, packet_loss: 0.0, jitter_ms: 0.5, is_up: true }
            ]
          }
        }
      }
    end

    it "allows Site to create measurements" do
      expect {
        post "/api/v1/measurements", params: measurement_params, headers: auth_headers(site), as: :json
      }.to change(Measurement, :count).by(1)

      expect(response).to have_http_status(:created)
    end

    it "denies User from creating measurements" do
      post "/api/v1/measurements", params: measurement_params, headers: auth_headers(user_admin), as: :json
      expect(response).to have_http_status(:forbidden)
    end

    it "denies Agent from creating measurements" do
      post "/api/v1/measurements", params: measurement_params, headers: auth_headers(agent), as: :json
      expect(response).to have_http_status(:forbidden)
    end

    it "denies ApiClient from creating measurements" do
      post "/api/v1/measurements", params: measurement_params, headers: auth_headers(api_client), as: :json
      expect(response).to have_http_status(:forbidden)
    end
  end

  describe "GET /api/v1/anomalies" do
    let!(:site_anomaly) { create(:anomaly, site: site) }
    let!(:other_anomaly) { create(:anomaly, site: other_site) }

    context "when authenticated as Site" do
      it "returns only own anomalies" do
        get "/api/v1/anomalies", headers: auth_headers(site)
        expect(response).to have_http_status(:ok)

        data = JSON.parse(response.body)["data"]
        expect(data.length).to eq(1)
        expect(data.first["id"]).to eq(site_anomaly.id.to_s)
      end
    end

    context "when authenticated as User" do
      it "returns all anomalies" do
        get "/api/v1/anomalies", headers: auth_headers(user_viewer)
        expect(response).to have_http_status(:ok)

        data = JSON.parse(response.body)["data"]
        expect(data.length).to eq(2)
      end
    end

    context "when authenticated as Agent" do
      it "returns all anomalies" do
        get "/api/v1/anomalies", headers: auth_headers(agent)
        expect(response).to have_http_status(:ok)

        data = JSON.parse(response.body)["data"]
        expect(data.length).to eq(2)
      end
    end
  end

  describe "PATCH /api/v1/anomalies/:id/resolve" do
    let!(:site_anomaly) { create(:anomaly, site: site) }
    let!(:other_anomaly) { create(:anomaly, site: other_site) }

    context "when authenticated as Site" do
      it "allows resolving own anomalies" do
        patch "/api/v1/anomalies/#{site_anomaly.id}/resolve", headers: auth_headers(site)
        expect(response).to have_http_status(:ok)
        expect(site_anomaly.reload.resolved_at).to be_present
      end

      it "denies resolving other sites' anomalies" do
        patch "/api/v1/anomalies/#{other_anomaly.id}/resolve", headers: auth_headers(site)
        expect(response).to have_http_status(:not_found)
      end
    end

    context "when authenticated as User (viewer)" do
      it "denies resolving anomalies" do
        patch "/api/v1/anomalies/#{site_anomaly.id}/resolve", headers: auth_headers(user_viewer)
        expect(response).to have_http_status(:forbidden)
      end
    end

    context "when authenticated as User (operator)" do
      it "allows resolving any anomaly" do
        patch "/api/v1/anomalies/#{other_anomaly.id}/resolve", headers: auth_headers(user_operator)
        expect(response).to have_http_status(:ok)
        expect(other_anomaly.reload.resolved_at).to be_present
      end
    end

    context "when authenticated as User (admin)" do
      it "allows resolving any anomaly" do
        patch "/api/v1/anomalies/#{site_anomaly.id}/resolve", headers: auth_headers(user_admin)
        expect(response).to have_http_status(:ok)
      end
    end

    context "when authenticated as Agent" do
      it "allows resolving any anomaly" do
        patch "/api/v1/anomalies/#{other_anomaly.id}/resolve", headers: auth_headers(agent)
        expect(response).to have_http_status(:ok)
      end
    end

    context "when authenticated as ApiClient" do
      it "denies resolving anomalies" do
        patch "/api/v1/anomalies/#{site_anomaly.id}/resolve", headers: auth_headers(api_client)
        expect(response).to have_http_status(:forbidden)
      end
    end
  end

  describe "GET /api/v1/baselines" do
    let!(:site_baseline) { create(:baseline, site: site) }
    let!(:other_baseline) { create(:baseline, site: other_site) }

    context "when authenticated as Site" do
      it "returns only own baselines" do
        get "/api/v1/baselines", headers: auth_headers(site)
        expect(response).to have_http_status(:ok)

        data = JSON.parse(response.body)["data"]
        expect(data.length).to eq(1)
      end
    end

    context "when authenticated as User" do
      it "returns all baselines" do
        get "/api/v1/baselines", headers: auth_headers(user_viewer)
        expect(response).to have_http_status(:ok)

        data = JSON.parse(response.body)["data"]
        expect(data.length).to eq(2)
      end
    end
  end

  describe "POST /api/v1/auth/token" do
    it "authenticates Site" do
      post "/api/v1/auth/token", params: {
        authenticatable_type: "site",
        identifier: site.name,
        secret: "test-secret-123"
      }, as: :json

      expect(response).to have_http_status(:ok)
      expect(JSON.parse(response.body)["data"]["access_token"]).to be_present
    end

    it "authenticates User" do
      user = create(:user, email: "test@example.com", password: "password123")
      post "/api/v1/auth/token", params: {
        authenticatable_type: "user",
        identifier: "test@example.com",
        secret: "password123"
      }, as: :json

      expect(response).to have_http_status(:ok)
      expect(JSON.parse(response.body)["data"]["access_token"]).to be_present
    end

    it "authenticates Agent" do
      post "/api/v1/auth/token", params: {
        authenticatable_type: "agent",
        identifier: agent.name,
        secret: "agent-secret-123"
      }, as: :json

      expect(response).to have_http_status(:ok)
      expect(JSON.parse(response.body)["data"]["access_token"]).to be_present
    end

    it "authenticates ApiClient" do
      post "/api/v1/auth/token", params: {
        authenticatable_type: "api_client",
        identifier: api_client.client_id,
        secret: "client-secret-123"
      }, as: :json

      expect(response).to have_http_status(:ok)
      expect(JSON.parse(response.body)["data"]["access_token"]).to be_present
    end

    it "denies suspended Agent" do
      suspended_agent = create(:agent, :suspended)
      post "/api/v1/auth/token", params: {
        authenticatable_type: "agent",
        identifier: suspended_agent.name,
        secret: "agent-secret-123"
      }, as: :json

      expect(response).to have_http_status(:forbidden)
    end

    it "denies deactivated ApiClient" do
      deactivated_client = create(:api_client, :deactivated)
      post "/api/v1/auth/token", params: {
        authenticatable_type: "api_client",
        identifier: deactivated_client.client_id,
        secret: "client-secret-123"
      }, as: :json

      expect(response).to have_http_status(:forbidden)
    end
  end
end
