require "rails_helper"

RSpec.describe AnomalyDetectionJob, type: :job do
  describe "#perform" do
    let(:site) { create(:site) }
    let!(:baseline) do
      create(:baseline,
        site: site,
        host: "test-host",
        ip: "192.168.1.1",
        latency_p95: 15.0
      )
    end

    context "with valid measurement IDs" do
      let!(:measurement) do
        create(:measurement,
          site: site,
          host: baseline.host,
          ip: baseline.ip,
          is_up: false
        )
      end

      it "detects anomalies for the measurements" do
        expect {
          described_class.new.perform([ measurement.id ])
        }.to change(Anomaly, :count).by(1)
      end

      it "delegates to AnomalyDetectionService" do
        expect(AnomalyDetectionService).to receive(:detect_for_batch)

        described_class.new.perform([ measurement.id ])
      end
    end

    context "with empty measurement IDs" do
      it "does not raise an error" do
        expect {
          described_class.new.perform([])
        }.not_to raise_error
      end

      it "does not call the service" do
        expect(AnomalyDetectionService).not_to receive(:detect_for_batch)

        described_class.new.perform([])
      end
    end

    context "with nil measurement IDs" do
      it "does not raise an error" do
        expect {
          described_class.new.perform(nil)
        }.not_to raise_error
      end
    end

    it "is enqueued to the default queue" do
      expect(described_class.new.queue_name).to eq("default")
    end
  end
end
