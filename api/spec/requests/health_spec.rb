require "rails_helper"

RSpec.describe "Health", type: :request do
  describe "GET /health" do
    it "returns ok status without authentication" do
      get "/health"

      expect(response).to have_http_status(:ok)
      json = JSON.parse(response.body)
      expect(json["status"]).to eq("ok")
      expect(json["timestamp"]).to be_present
    end

    it "returns valid ISO8601 timestamp" do
      get "/health"

      json = JSON.parse(response.body)
      expect { Time.iso8601(json["timestamp"]) }.not_to raise_error
    end
  end
end
