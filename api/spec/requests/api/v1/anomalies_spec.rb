require "rails_helper"

RSpec.describe "Api::V1::Anomalies", type: :request do
  let(:site) { create(:site) }
  let(:headers) { auth_headers(site) }

  describe "GET /api/v1/anomalies" do
    before do
      create(:anomaly, site: site, severity: :warning)
      create(:anomaly, :critical, site: site)
      create(:anomaly, :resolved, site: site)
    end

    it "returns anomalies for current site in JSON:API format" do
      get "/api/v1/anomalies", headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"]).to be_an(Array)
      expect(json["data"].length).to eq(3)
      expect(json["data"].first).to include("type" => "anomalies")
    end

    it "filters active anomalies" do
      get "/api/v1/anomalies", params: { active: "true" }, headers: headers

      json = json_response
      expect(json["data"].length).to eq(2) # excludes resolved
      json["data"].each do |anomaly|
        expect(anomaly["attributes"]["resolved_at"]).to be_nil
      end
    end

    it "filters by severity" do
      get "/api/v1/anomalies", params: { severity: "critical" }, headers: headers

      json = json_response
      expect(json["data"].length).to eq(1)
      expect(json["data"].first["attributes"]["severity"]).to eq("critical")
    end

    it "does not return anomalies from other sites" do
      other_site = create(:site)
      create(:anomaly, site: other_site)

      get "/api/v1/anomalies", headers: headers

      json = json_response
      expect(json["data"].length).to eq(3)
    end

    it "filters by status=active" do
      get "/api/v1/anomalies", params: { status: "active" }, headers: headers

      json = json_response
      expect(json["data"].length).to eq(2)
      json["data"].each do |anomaly|
        expect(anomaly["attributes"]["active"]).to be true
      end
    end

    it "filters by status=resolved" do
      get "/api/v1/anomalies", params: { status: "resolved" }, headers: headers

      json = json_response
      expect(json["data"].length).to eq(1)
      expect(json["data"].first["attributes"]["resolved_at"]).not_to be_nil
    end

    it "returns all anomalies with status=all" do
      get "/api/v1/anomalies", params: { status: "all" }, headers: headers

      json = json_response
      expect(json["data"].length).to eq(3)
    end

    it "filters by since timestamp" do
      old_anomaly = create(:anomaly, site: site, updated_at: 2.hours.ago)

      get "/api/v1/anomalies", params: { since: 1.hour.ago.iso8601 }, headers: headers

      json = json_response
      ids = json["data"].map { |a| a["id"].to_i }
      expect(ids).not_to include(old_anomaly.id)
    end

    it "returns 400 for invalid since parameter" do
      get "/api/v1/anomalies", params: { since: "not-a-date" }, headers: headers

      expect(response).to have_http_status(:bad_request)
      expect(json_response["errors"]).to be_present
    end

    it "includes meta with counts" do
      get "/api/v1/anomalies", headers: headers

      json = json_response
      expect(json["meta"]).to include(
        "total" => 3,
        "active" => 2,
        "resolved" => 1
      )
    end

    it "includes created_at in attributes" do
      get "/api/v1/anomalies", headers: headers

      json = json_response
      expect(json["data"].first["attributes"]).to have_key("created_at")
    end

    it "includes duration for resolved anomalies" do
      get "/api/v1/anomalies", params: { status: "resolved" }, headers: headers

      json = json_response
      resolved_anomaly = json["data"].first
      expect(resolved_anomaly["attributes"]).to have_key("duration")
      expect(resolved_anomaly["attributes"]["duration"]).not_to be_nil
    end
  end

  describe "GET /api/v1/anomalies/history" do
    before do
      create(:anomaly, site: site, host: "router")
      create(:anomaly, :resolved, site: site, host: "router")
      create(:anomaly, site: site, host: "switch")
    end

    it "returns anomalies for the specified host" do
      get "/api/v1/anomalies/history", params: { host: "router" }, headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"].length).to eq(2)
      json["data"].each do |anomaly|
        expect(anomaly["attributes"]["host"]).to eq("router")
      end
    end

    it "requires host parameter" do
      get "/api/v1/anomalies/history", headers: headers

      expect(response).to have_http_status(:bad_request)
    end

    it "respects days parameter" do
      old_anomaly = create(:anomaly, site: site, host: "router", created_at: 10.days.ago)

      get "/api/v1/anomalies/history", params: { host: "router", days: 7 }, headers: headers

      json = json_response
      ids = json["data"].map { |a| a["id"].to_i }
      expect(ids).not_to include(old_anomaly.id)
    end
  end

  describe "GET /api/v1/anomalies/:id" do
    let(:anomaly) { create(:anomaly, :latency_spike, site: site) }

    it "returns anomaly in JSON:API format" do
      get "/api/v1/anomalies/#{anomaly.id}", headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"]["type"]).to eq("anomalies")
      expect(json["data"]["attributes"]["anomaly_type"]).to eq("latency_spike")
      expect(json["data"]["attributes"]["current_value"]).to eq(250.0)
    end

    it "returns 404 for non-existent anomaly" do
      get "/api/v1/anomalies/99999", headers: headers

      expect(response).to have_http_status(:not_found)
    end

    it "returns 404 for anomaly from another site" do
      other_site = create(:site)
      other_anomaly = create(:anomaly, site: other_site)

      get "/api/v1/anomalies/#{other_anomaly.id}", headers: headers

      expect(response).to have_http_status(:not_found)
    end
  end

  describe "PATCH /api/v1/anomalies/:id/resolve" do
    let(:anomaly) { create(:anomaly, site: site) }

    it "resolves the anomaly" do
      expect(anomaly.resolved_at).to be_nil

      patch "/api/v1/anomalies/#{anomaly.id}/resolve", headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"]["attributes"]["resolved_at"]).not_to be_nil
      expect(anomaly.reload.resolved_at).to be_present
    end

    it "returns 404 for anomaly from another site" do
      other_site = create(:site)
      other_anomaly = create(:anomaly, site: other_site)

      patch "/api/v1/anomalies/#{other_anomaly.id}/resolve", headers: headers

      expect(response).to have_http_status(:not_found)
    end
  end
end
