require "rails_helper"

RSpec.describe "Api::V1::Measurements", type: :request do
  let(:site) { create(:site) }
  let(:headers) { auth_headers(site) }

  describe "POST /api/v1/measurements" do
    let(:valid_params) do
      {
        data: {
          attributes: {
            site: site.name,
            timestamp: Time.current.iso8601,
            measurements: [
              { host: "router.local", ip: "192.168.1.1", latency_ms: 5.2, packet_loss: 0, jitter_ms: 0.5, is_up: true },
              { host: "google.com", ip: "8.8.8.8", latency_ms: 25.0, packet_loss: 0, jitter_ms: 2.1, is_up: true }
            ]
          }
        }
      }
    end

    context "with valid data" do
      it "creates measurements and returns batch info" do
        expect {
          post "/api/v1/measurements", params: valid_params, headers: headers
        }.to change(Measurement, :count).by(2)

        expect(response).to have_http_status(:created)
        json = json_response
        expect(json["data"]["attributes"]["count"]).to eq(2)
        expect(json["data"]["attributes"]["site_name"]).to eq(site.name)
      end

      it "associates measurements with authenticated site" do
        post "/api/v1/measurements", params: valid_params, headers: headers

        expect(site.measurements.count).to eq(2)
        expect(site.measurements.pluck(:host)).to contain_exactly("router.local", "google.com")
      end
    end

    context "with invalid data" do
      it "returns 422 for missing required fields" do
        invalid_params = {
          data: {
            attributes: {
              timestamp: Time.current.iso8601,
              measurements: [
                { ip: "192.168.1.1", latency_ms: 5.2 } # missing host
              ]
            }
          }
        }

        post "/api/v1/measurements", params: invalid_params, headers: headers

        expect(response).to have_http_status(:unprocessable_entity)
      end
    end

    it "returns 401 without authorization" do
      post "/api/v1/measurements", params: valid_params

      expect(response).to have_http_status(:unauthorized)
    end
  end

  describe "GET /api/v1/measurements" do
    before do
      create_list(:measurement, 5, site: site)
      create(:measurement, site: site, host: "special-host")
    end

    it "returns measurements for current site in JSON:API format" do
      get "/api/v1/measurements", headers: headers

      expect(response).to have_http_status(:ok)
      json = json_response
      expect(json["data"]).to be_an(Array)
      expect(json["data"].length).to eq(6)
    end

    it "filters by host" do
      get "/api/v1/measurements", params: { host: "special-host" }, headers: headers

      json = json_response
      expect(json["data"].length).to eq(1)
      expect(json["data"].first["attributes"]["host"]).to eq("special-host")
    end

    it "respects limit parameter" do
      get "/api/v1/measurements", params: { limit: 2 }, headers: headers

      json = json_response
      expect(json["data"].length).to eq(2)
    end

    it "does not return measurements from other sites" do
      other_site = create(:site)
      create(:measurement, site: other_site)

      get "/api/v1/measurements", headers: headers

      json = json_response
      # Should only return 6 measurements from our site, not the one from other_site
      expect(json["data"].length).to eq(6)
    end
  end
end
