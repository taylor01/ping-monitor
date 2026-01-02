require "rails_helper"

RSpec.describe "Api::V1::Sites", type: :request do
  let(:site) { create(:site) }
  let(:headers) { auth_headers(site) }

  describe "GET /api/v1/sites" do
    before { create_list(:site, 3) }

    it "returns all sites in JSON:API format" do
      get "/api/v1/sites", headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"]).to be_an(Array)
      expect(json["data"].length).to eq(4) # 3 + our authenticated site
      expect(json["data"].first["type"]).to eq("sites")
      expect(json["data"].first).to have_key("id")
      expect(json["data"].first).to have_key("attributes")
    end

    it "returns 401 without authorization" do
      get "/api/v1/sites"

      expect(response).to have_http_status(:unauthorized)
    end
  end

  describe "GET /api/v1/sites/:id" do
    let(:other_site) { create(:site, :with_measurements) }

    it "returns site in JSON:API format" do
      get "/api/v1/sites/#{other_site.id}", headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"]["type"]).to eq("sites")
      expect(json["data"]["attributes"]["name"]).to eq(other_site.name)
    end

    it "returns 404 for non-existent site" do
      get "/api/v1/sites/99999", headers: headers

      expect(response).to have_http_status(:not_found)
      expect(json_response["errors"]).to be_present
    end
  end

  describe "GET /api/v1/sites/me" do
    it "returns the authenticated site" do
      get "/api/v1/sites/me", headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"]["id"]).to eq(site.id.to_s)
      expect(json["data"]["attributes"]["name"]).to eq(site.name)
    end

    it "includes healthy attribute" do
      site.update(last_heartbeat: Time.current)

      get "/api/v1/sites/me", headers: headers

      json = json_response
      expect(json["data"]["attributes"]["healthy"]).to be true
    end

    it "returns 401 with expired token" do
      get "/api/v1/sites/me", headers: expired_auth_headers(site)

      expect(response).to have_http_status(:unauthorized)
    end
  end

  describe "GET /api/v1/sites/:id/status" do
    let(:status_site) { create(:site, :with_measurements) }

    before do
      # Create some measurements with different statuses
      create(:measurement, site: status_site, host: "router", is_up: true, latency_ms: 5.0)
      create(:measurement, site: status_site, host: "switch", is_up: true, latency_ms: 3.0)
      create(:measurement, site: status_site, host: "server", is_up: false)

      # Create an active anomaly
      create(:anomaly, site: status_site, host: "server")
    end

    it "returns site status in JSON:API format" do
      get "/api/v1/sites/#{status_site.id}/status", headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"]["type"]).to eq("site_status")
      expect(json["data"]["attributes"]["name"]).to eq(status_site.name)
    end

    it "includes device counts" do
      get "/api/v1/sites/#{status_site.id}/status", headers: headers

      json = json_response
      attrs = json["data"]["attributes"]
      expect(attrs["devices_total"]).to be >= 3
      expect(attrs["devices_up"]).to be >= 2
      expect(attrs["devices_down"]).to be >= 1
    end

    it "includes overall status based on device health" do
      get "/api/v1/sites/#{status_site.id}/status", headers: headers

      json = json_response
      expect(json["data"]["attributes"]["status"]).to be_in(%w[healthy degraded critical])
    end

    it "includes active anomaly count" do
      get "/api/v1/sites/#{status_site.id}/status", headers: headers

      json = json_response
      expect(json["data"]["attributes"]["active_anomalies"]).to eq(1)
    end

    it "includes devices list with metrics" do
      get "/api/v1/sites/#{status_site.id}/status", headers: headers

      json = json_response
      devices = json["data"]["attributes"]["devices"]
      expect(devices).to be_an(Array)
      expect(devices.first).to include("host", "ip", "is_up")
    end

    it "returns 404 for non-existent site" do
      get "/api/v1/sites/99999/status", headers: headers

      expect(response).to have_http_status(:not_found)
    end
  end
end
