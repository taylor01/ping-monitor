require "rails_helper"

RSpec.describe Measurement, type: :model do
  describe "associations" do
    it { should belong_to(:site) }
    it { should have_many(:anomalies).dependent(:nullify) }
  end

  describe "validations" do
    it { should validate_presence_of(:host) }
    it { should validate_presence_of(:ip) }
    it { should validate_presence_of(:timestamp) }

    it "validates is_up inclusion" do
      measurement = build(:measurement, is_up: nil)
      expect(measurement).not_to be_valid
    end

    it "accepts true for is_up" do
      measurement = build(:measurement, is_up: true)
      expect(measurement).to be_valid
    end

    it "accepts false for is_up" do
      measurement = build(:measurement, is_up: false, latency_ms: nil)
      expect(measurement).to be_valid
    end
  end

  describe "scopes" do
    let(:site) { create(:site) }

    describe ".up" do
      it "returns measurements where host is up" do
        up = create(:measurement, site: site, is_up: true)
        down = create(:measurement, :down, site: site)

        expect(Measurement.up).to include(up)
        expect(Measurement.up).not_to include(down)
      end
    end

    describe ".down" do
      it "returns measurements where host is down" do
        up = create(:measurement, site: site, is_up: true)
        down = create(:measurement, :down, site: site)

        expect(Measurement.down).not_to include(up)
        expect(Measurement.down).to include(down)
      end
    end

    describe ".recent" do
      it "returns measurements since specified time" do
        recent = create(:measurement, site: site, timestamp: 30.minutes.ago)
        old = create(:measurement, site: site, timestamp: 2.hours.ago)

        expect(Measurement.recent(1.hour.ago)).to include(recent)
        expect(Measurement.recent(1.hour.ago)).not_to include(old)
      end

      it "defaults to 1 hour" do
        recent = create(:measurement, site: site, timestamp: 30.minutes.ago)
        old = create(:measurement, site: site, timestamp: 2.hours.ago)

        expect(Measurement.recent).to include(recent)
        expect(Measurement.recent).not_to include(old)
      end
    end

    describe ".for_host" do
      it "returns measurements for specified host" do
        router = create(:measurement, site: site, host: "router")
        switch = create(:measurement, site: site, host: "switch")

        expect(Measurement.for_host("router")).to include(router)
        expect(Measurement.for_host("router")).not_to include(switch)
      end
    end
  end

  describe "callbacks" do
    describe "after_create" do
      it "updates site heartbeat" do
        site = create(:site, last_heartbeat: 1.hour.ago)
        before_create = Time.current

        create(:measurement, site: site)
        site.reload

        expect(site.last_heartbeat).to be >= before_create
        expect(site.last_heartbeat).to be_within(2.seconds).of(Time.current)
      end
    end
  end

  describe "traits" do
    describe ":down" do
      it "creates a down measurement" do
        measurement = build(:measurement, :down)
        expect(measurement.is_up).to be false
        expect(measurement.latency_ms).to be_nil
        expect(measurement.packet_loss).to eq(100.0)
      end
    end

    describe ":high_latency" do
      it "creates a high latency measurement" do
        measurement = build(:measurement, :high_latency)
        expect(measurement.latency_ms).to be >= 200.0
      end
    end
  end
end
