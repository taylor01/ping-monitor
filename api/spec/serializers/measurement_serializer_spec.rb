require "rails_helper"

RSpec.describe MeasurementSerializer do
  let(:site) { create(:site) }
  let(:measurement) { create(:measurement, site: site, host: "router", ip: "192.168.1.1", latency_ms: 15.5) }

  describe "serialization" do
    subject { described_class.new(measurement).serializable_hash }

    it "returns correct type" do
      expect(subject[:data][:type]).to eq(:measurements)
    end

    it "includes id" do
      expect(subject[:data][:id]).to eq(measurement.id.to_s)
    end

    it "includes host attribute" do
      expect(subject[:data][:attributes][:host]).to eq("router")
    end

    it "includes ip attribute" do
      expect(subject[:data][:attributes][:ip]).to eq("192.168.1.1")
    end

    it "includes latency_ms attribute" do
      expect(subject[:data][:attributes][:latency_ms]).to eq(15.5)
    end

    it "includes packet_loss attribute" do
      expect(subject[:data][:attributes][:packet_loss]).to be_present
    end

    it "includes jitter_ms attribute" do
      expect(subject[:data][:attributes][:jitter_ms]).to be_present
    end

    it "includes is_up attribute" do
      expect(subject[:data][:attributes][:is_up]).to be true
    end

    it "includes timestamp attribute" do
      expect(subject[:data][:attributes][:timestamp]).to be_present
    end

    it "includes site relationship" do
      expect(subject[:data][:relationships][:site][:data][:id]).to eq(site.id.to_s)
    end
  end

  describe "collection serialization" do
    let!(:measurements) { create_list(:measurement, 3, site: site) }

    it "serializes multiple measurements" do
      result = described_class.new(measurements).serializable_hash
      expect(result[:data].length).to eq(3)
      expect(result[:data]).to all(have_key(:type))
    end
  end
end
