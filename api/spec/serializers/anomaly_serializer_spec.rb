require "rails_helper"

RSpec.describe AnomalySerializer do
  let(:site) { create(:site) }
  let(:anomaly) { create(:anomaly, :latency_spike, site: site) }

  describe "serialization" do
    subject { described_class.new(anomaly).serializable_hash }

    it "returns correct type" do
      expect(subject[:data][:type]).to eq(:anomalies)
    end

    it "includes id" do
      expect(subject[:data][:id]).to eq(anomaly.id.to_s)
    end

    it "includes host attribute" do
      expect(subject[:data][:attributes][:host]).to be_present
    end

    it "includes anomaly_type attribute" do
      expect(subject[:data][:attributes][:anomaly_type]).to eq("latency_spike")
    end

    it "includes severity attribute" do
      expect(subject[:data][:attributes][:severity]).to be_present
    end

    it "includes message attribute" do
      expect(subject[:data][:attributes][:message]).to be_present
    end

    it "includes current_value attribute" do
      expect(subject[:data][:attributes][:current_value]).to eq(250.0)
    end

    it "includes baseline_value attribute" do
      expect(subject[:data][:attributes][:baseline_value]).to eq(25.0)
    end

    it "includes resolved_at attribute" do
      expect(subject[:data][:attributes]).to have_key(:resolved_at)
    end

    it "includes active computed attribute" do
      expect(subject[:data][:attributes][:active]).to be true
    end

    it "includes site relationship" do
      expect(subject[:data][:relationships][:site][:data][:id]).to eq(site.id.to_s)
    end
  end

  describe "resolved anomaly" do
    let(:resolved_anomaly) { create(:anomaly, :resolved, site: site) }

    it "shows active as false" do
      result = described_class.new(resolved_anomaly).serializable_hash
      expect(result[:data][:attributes][:active]).to be false
    end

    it "shows resolved_at timestamp" do
      result = described_class.new(resolved_anomaly).serializable_hash
      expect(result[:data][:attributes][:resolved_at]).to be_present
    end
  end

  describe "measurement relationship" do
    let(:measurement) { create(:measurement, site: site) }
    let(:anomaly_with_measurement) { create(:anomaly, site: site, measurement: measurement) }

    it "includes measurement when present" do
      result = described_class.new(anomaly_with_measurement).serializable_hash
      expect(result[:data][:relationships][:measurement][:data][:id]).to eq(measurement.id.to_s)
    end

    it "excludes measurement when not present" do
      anomaly_without = create(:anomaly, site: site, measurement: nil)
      result = described_class.new(anomaly_without).serializable_hash
      expect(result[:data][:relationships]).not_to have_key(:measurement)
    end
  end
end
