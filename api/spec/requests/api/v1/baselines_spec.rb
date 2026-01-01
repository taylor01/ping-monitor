require "rails_helper"

RSpec.describe "Api::V1::Baselines", type: :request do
  let(:site) { create(:site) }
  let(:headers) { auth_headers(site) }

  describe "GET /api/v1/baselines" do
    context "when baselines exist" do
      let!(:baseline1) do
        create(:baseline,
          site: site,
          host: "host-a",
          ip: "192.168.1.1",
          latency_mean: 10.0,
          latency_p95: 15.0
        )
      end

      let!(:baseline2) do
        create(:baseline,
          site: site,
          host: "host-b",
          ip: "192.168.1.2",
          latency_mean: 20.0,
          latency_p95: 25.0
        )
      end

      it "returns all baselines for the site" do
        get "/api/v1/baselines", headers: headers

        expect(response).to have_http_status(:ok)
        expect(json_response["data"].size).to eq(2)
      end

      it "returns baselines ordered by host" do
        get "/api/v1/baselines", headers: headers

        hosts = json_response["data"].map { |b| b["id"] }
        expect(hosts).to eq(%w[host-a host-b])
      end

      it "includes baseline attributes" do
        get "/api/v1/baselines", headers: headers

        baseline_data = json_response["data"].first["attributes"]
        expect(baseline_data["host"]).to eq("host-a")
        expect(baseline_data["latency_mean"]).to eq(10.0)
        expect(baseline_data["latency_p95"]).to eq(15.0)
      end

      it "includes computed thresholds" do
        get "/api/v1/baselines", headers: headers

        thresholds = json_response["data"].first["attributes"]["thresholds"]
        expect(thresholds["warning"]).to eq(22.5)  # p95 * 1.5
        expect(thresholds["critical"]).to eq(30.0) # p95 * 2.0
      end
    end

    context "when no baselines exist" do
      it "returns an empty array" do
        get "/api/v1/baselines", headers: headers

        expect(response).to have_http_status(:ok)
        expect(json_response["data"]).to eq([])
      end
    end

    context "with multiple sites" do
      let(:other_site) { create(:site) }
      let!(:own_baseline) { create(:baseline, site: site, host: "my-host") }
      let!(:other_baseline) { create(:baseline, site: other_site, host: "other-host") }

      it "only returns baselines for the authenticated site" do
        get "/api/v1/baselines", headers: headers

        expect(json_response["data"].size).to eq(1)
        expect(json_response["data"].first["id"]).to eq("my-host")
      end
    end

    context "without authentication" do
      it "returns 401 unauthorized" do
        get "/api/v1/baselines"

        expect(response).to have_http_status(:unauthorized)
      end
    end
  end

  describe "GET /api/v1/baselines/:host" do
    context "when baseline exists" do
      let!(:baseline) do
        create(:baseline,
          site: site,
          host: "test-host",
          ip: "192.168.1.1",
          latency_mean: 10.0,
          latency_stddev: 2.0,
          latency_p95: 15.0,
          latency_p99: 20.0,
          sample_count: 100
        )
      end

      it "returns the baseline" do
        get "/api/v1/baselines/test-host", headers: headers

        expect(response).to have_http_status(:ok)
        expect(json_response["data"]["id"]).to eq("test-host")
      end

      it "includes all baseline attributes" do
        get "/api/v1/baselines/test-host", headers: headers

        attrs = json_response["data"]["attributes"]
        expect(attrs["host"]).to eq("test-host")
        expect(attrs["ip"]).to eq("192.168.1.1")
        expect(attrs["latency_mean"]).to eq(10.0)
        expect(attrs["latency_stddev"]).to eq(2.0)
        expect(attrs["latency_p95"]).to eq(15.0)
        expect(attrs["latency_p99"]).to eq(20.0)
        expect(attrs["sample_count"]).to eq(100)
      end
    end

    context "when baseline does not exist" do
      it "returns 404 not found" do
        get "/api/v1/baselines/nonexistent-host", headers: headers

        expect(response).to have_http_status(:not_found)
        expect(json_response["errors"].first["code"]).to eq("not_found")
        expect(json_response["errors"].first["detail"]).to include("nonexistent-host")
      end
    end

    context "when baseline belongs to another site" do
      let(:other_site) { create(:site) }
      let!(:other_baseline) { create(:baseline, site: other_site, host: "other-host") }

      it "returns 404 not found" do
        get "/api/v1/baselines/other-host", headers: headers

        expect(response).to have_http_status(:not_found)
      end
    end

    context "without authentication" do
      it "returns 401 unauthorized" do
        get "/api/v1/baselines/any-host"

        expect(response).to have_http_status(:unauthorized)
      end
    end
  end
end
