require "rails_helper"

RSpec.describe SiteHealthCheckJob, type: :job do
  describe "#perform" do
    context "when site has recent heartbeat" do
      let!(:site) { create(:site, last_heartbeat: 1.minute.ago, status: "healthy") }

      it "does not create an anomaly" do
        expect {
          described_class.new.perform
        }.not_to change(Anomaly, :count)
      end

      it "keeps site status as healthy" do
        described_class.new.perform

        site.reload
        expect(site.status).to eq("healthy")
      end
    end

    context "when site heartbeat is stale" do
      let!(:site) { create(:site, last_heartbeat: 10.minutes.ago, status: "healthy") }

      it "creates a site_offline anomaly" do
        expect {
          described_class.new.perform
        }.to change(Anomaly, :count).by(1)

        anomaly = Anomaly.last
        expect(anomaly.anomaly_type).to eq("site_offline")
        expect(anomaly.severity).to eq("critical")
      end

      it "updates site status to offline" do
        described_class.new.perform

        site.reload
        expect(site.status).to eq("offline")
      end

      it "does not create duplicate anomalies" do
        described_class.new.perform

        expect {
          described_class.new.perform
        }.not_to change(Anomaly, :count)
      end
    end

    context "when site has no heartbeat" do
      let!(:site) { create(:site, last_heartbeat: nil, status: "unknown") }

      it "creates a site_offline anomaly" do
        expect {
          described_class.new.perform
        }.to change(Anomaly, :count).by(1)
      end

      it "updates site status to offline" do
        described_class.new.perform

        site.reload
        expect(site.status).to eq("offline")
      end
    end

    context "when site comes back online" do
      let!(:site) { create(:site, last_heartbeat: 1.minute.ago, status: "offline") }
      let!(:offline_anomaly) do
        create(:anomaly,
          site: site,
          anomaly_type: :site_offline,
          severity: :critical
        )
      end

      it "resolves the site_offline anomaly" do
        described_class.new.perform

        offline_anomaly.reload
        expect(offline_anomaly.active?).to be false
        expect(offline_anomaly.resolved_at).to be_present
      end

      it "updates site status based on remaining anomalies" do
        described_class.new.perform

        site.reload
        expect(site.status).to eq("healthy")
      end
    end

    context "when online site has active critical anomalies" do
      let!(:site) { create(:site, last_heartbeat: 1.minute.ago, status: "healthy") }
      let!(:critical_anomaly) do
        create(:anomaly,
          site: site,
          host: "test-host",
          anomaly_type: :host_down,
          severity: :critical
        )
      end

      it "updates site status to critical" do
        described_class.new.perform

        site.reload
        expect(site.status).to eq("critical")
      end
    end

    context "when online site has active warning anomalies" do
      let!(:site) { create(:site, last_heartbeat: 1.minute.ago, status: "healthy") }
      let!(:warning_anomaly) do
        create(:anomaly,
          site: site,
          host: "test-host",
          anomaly_type: :latency_spike,
          severity: :warning
        )
      end

      it "updates site status to warning" do
        described_class.new.perform

        site.reload
        expect(site.status).to eq("warning")
      end
    end

    it "is enqueued to the default queue" do
      expect(described_class.new.queue_name).to eq("default")
    end
  end
end
