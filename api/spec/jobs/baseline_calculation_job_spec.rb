require "rails_helper"

RSpec.describe BaselineCalculationJob, type: :job do
  describe "#perform" do
    let!(:site1) { create(:site, name: "site-1") }
    let!(:site2) { create(:site, name: "site-2") }

    before do
      # Create enough measurements for baselines
      [ site1, site2 ].each do |site|
        70.times do |i|
          create(:measurement,
            site: site,
            host: "host-1",
            ip: "192.168.1.1",
            is_up: true,
            latency_ms: 10.0 + rand(5),
            timestamp: i.minutes.ago
          )
        end
      end
    end

    it "calculates baselines for all sites" do
      expect {
        described_class.new.perform
      }.to change(Baseline, :count).by(2)
    end

    it "delegates to BaselineCalculationService" do
      expect(BaselineCalculationService).to receive(:calculate_for_site).with(site1)
      expect(BaselineCalculationService).to receive(:calculate_for_site).with(site2)

      described_class.new.perform
    end

    it "is enqueued to the default queue" do
      expect(described_class.new.queue_name).to eq("default")
    end
  end
end
