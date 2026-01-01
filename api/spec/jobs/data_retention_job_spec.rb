require "rails_helper"

RSpec.describe DataRetentionJob, type: :job do
  describe "#perform" do
    let(:site) { create(:site) }

    context "with old measurements" do
      before do
        # Create measurements older than retention period
        5.times do |i|
          create(:measurement,
            site: site,
            host: "test-host",
            ip: "192.168.1.1",
            timestamp: 10.days.ago + i.hours
          )
        end

        # Create recent measurements
        5.times do |i|
          create(:measurement,
            site: site,
            host: "test-host",
            ip: "192.168.1.1",
            timestamp: 1.day.ago + i.hours
          )
        end
      end

      it "deletes measurements older than retention period" do
        expect {
          described_class.new.perform
        }.to change(Measurement, :count).by(-5)
      end

      it "keeps recent measurements" do
        described_class.new.perform

        expect(Measurement.where("timestamp > ?", 7.days.ago).count).to eq(5)
      end
    end

    context "with no old measurements" do
      before do
        3.times do |i|
          create(:measurement,
            site: site,
            host: "test-host",
            ip: "192.168.1.1",
            timestamp: 1.day.ago + i.hours
          )
        end
      end

      it "does not delete any measurements" do
        expect {
          described_class.new.perform
        }.not_to change(Measurement, :count)
      end
    end

    context "with anomalies" do
      before do
        # Create old resolved anomaly
        create(:anomaly,
          site: site,
          host: "test-host",
          anomaly_type: :host_down,
          severity: :critical,
          created_at: 60.days.ago,
          resolved_at: 59.days.ago
        )

        # Create recent anomaly
        create(:anomaly,
          site: site,
          host: "test-host",
          anomaly_type: :latency_spike,
          severity: :warning
        )
      end

      it "keeps all anomalies for availability history" do
        expect {
          described_class.new.perform
        }.not_to change(Anomaly, :count)
      end
    end

    it "is enqueued to the default queue" do
      expect(described_class.new.queue_name).to eq("default")
    end
  end
end
