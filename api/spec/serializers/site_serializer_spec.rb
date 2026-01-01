require "rails_helper"

RSpec.describe SiteSerializer do
  let(:site) { create(:site, :with_measurements, status: :healthy, last_heartbeat: Time.current) }

  describe "serialization" do
    subject { described_class.new(site).serializable_hash }

    it "returns correct type" do
      expect(subject[:data][:type]).to eq(:sites)
    end

    it "includes id" do
      expect(subject[:data][:id]).to eq(site.id.to_s)
    end

    it "includes name attribute" do
      expect(subject[:data][:attributes][:name]).to eq(site.name)
    end

    it "includes status attribute" do
      expect(subject[:data][:attributes][:status]).to eq("healthy")
    end

    it "includes last_heartbeat attribute" do
      expect(subject[:data][:attributes][:last_heartbeat]).to be_present
    end

    it "includes healthy computed attribute" do
      expect(subject[:data][:attributes][:healthy]).to be true
    end

    it "includes hosts_count computed attribute" do
      expect(subject[:data][:attributes][:hosts_count]).to eq(5)
    end
  end

  describe "conditional relationships" do
    it "excludes measurements by default" do
      result = described_class.new(site).serializable_hash
      relationships = result[:data][:relationships] || {}
      expect(relationships).not_to have_key(:measurements)
    end

    it "includes measurements when requested" do
      result = described_class.new(site, params: { include_measurements: true }).serializable_hash
      expect(result[:data][:relationships]).to have_key(:measurements)
    end

    it "includes anomalies when requested" do
      create(:anomaly, site: site)
      result = described_class.new(site, params: { include_anomalies: true }).serializable_hash
      expect(result[:data][:relationships]).to have_key(:anomalies)
    end
  end
end
