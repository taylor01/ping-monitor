require "rails_helper"

RSpec.describe AnomalyDetectionService do
  let(:site) { create(:site) }
  let(:baseline) do
    create(:baseline,
      site: site,
      host: "test-host",
      ip: "192.168.1.1",
      latency_mean: 10.0,
      latency_stddev: 2.0,
      latency_p95: 15.0,
      latency_p99: 20.0,
      sample_count: 100
    )
  end

  describe ".detect_for_measurement" do
    context "with no baseline (cold start)" do
      let(:measurement) do
        create(:measurement,
          site: site,
          host: "new-host",
          ip: "192.168.1.99",
          is_up: false,
          latency_ms: nil
        )
      end

      it "does not create any anomalies" do
        expect {
          described_class.detect_for_measurement(measurement)
        }.not_to change(Anomaly, :count)
      end
    end

    context "host down detection" do
      let!(:baseline_record) { baseline }

      context "when host goes down" do
        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: false,
            latency_ms: nil
          )
        end

        it "creates a host_down anomaly" do
          expect {
            described_class.detect_for_measurement(measurement)
          }.to change(Anomaly, :count).by(1)

          anomaly = Anomaly.last
          expect(anomaly.anomaly_type).to eq("host_down")
          expect(anomaly.severity).to eq("critical")
          expect(anomaly.host).to eq(baseline.host)
          expect(anomaly.active?).to be true
        end

        it "does not create duplicate anomalies for ongoing outage" do
          described_class.detect_for_measurement(measurement)

          second_measurement = create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: false,
            latency_ms: nil
          )

          expect {
            described_class.detect_for_measurement(second_measurement)
          }.not_to change(Anomaly, :count)
        end
      end

      context "when host recovers" do
        let!(:active_anomaly) do
          create(:anomaly,
            site: site,
            host: baseline.host,
            anomaly_type: :host_down,
            severity: :critical
          )
        end

        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: true,
            latency_ms: 10.0
          )
        end

        it "resolves the host_down anomaly" do
          described_class.detect_for_measurement(measurement)

          active_anomaly.reload
          expect(active_anomaly.active?).to be false
          expect(active_anomaly.resolved_at).to be_present
        end

        it "creates a host_recovery anomaly" do
          expect {
            described_class.detect_for_measurement(measurement)
          }.to change { Anomaly.where(anomaly_type: :host_recovery).count }.by(1)

          recovery = Anomaly.where(anomaly_type: :host_recovery).last
          expect(recovery.severity).to eq("info")
        end
      end
    end

    context "latency spike detection" do
      let!(:baseline_record) { baseline }

      context "when latency exceeds warning threshold" do
        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: true,
            latency_ms: baseline.latency_p95 * 1.6  # > 1.5x p95
          )
        end

        it "creates a warning latency_spike anomaly" do
          expect {
            described_class.detect_for_measurement(measurement)
          }.to change(Anomaly, :count).by(1)

          anomaly = Anomaly.last
          expect(anomaly.anomaly_type).to eq("latency_spike")
          expect(anomaly.severity).to eq("warning")
        end
      end

      context "when latency exceeds critical threshold" do
        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: true,
            latency_ms: baseline.latency_p95 * 2.5  # > 2.0x p95
          )
        end

        it "creates a critical latency_spike anomaly" do
          expect {
            described_class.detect_for_measurement(measurement)
          }.to change(Anomaly, :count).by(1)

          anomaly = Anomaly.last
          expect(anomaly.anomaly_type).to eq("latency_spike")
          expect(anomaly.severity).to eq("critical")
        end
      end

      context "when latency returns to normal" do
        let!(:active_latency_anomaly) do
          create(:anomaly,
            site: site,
            host: baseline.host,
            anomaly_type: :latency_spike,
            severity: :warning
          )
        end

        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: true,
            latency_ms: baseline.latency_p95 * 1.2  # < 1.5x p95 (normal)
          )
        end

        it "resolves the latency_spike anomaly" do
          described_class.detect_for_measurement(measurement)

          active_latency_anomaly.reload
          expect(active_latency_anomaly.active?).to be false
        end
      end

      context "when latency is normal" do
        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: true,
            latency_ms: baseline.latency_mean
          )
        end

        it "does not create any anomalies" do
          expect {
            described_class.detect_for_measurement(measurement)
          }.not_to change(Anomaly, :count)
        end
      end
    end

    context "packet loss detection" do
      let!(:baseline_record) { baseline }

      context "when packet loss exceeds warning threshold" do
        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: true,
            latency_ms: 10.0,
            packet_loss: 15.0  # > 10%
          )
        end

        it "creates a warning packet_loss anomaly" do
          expect {
            described_class.detect_for_measurement(measurement)
          }.to change(Anomaly, :count).by(1)

          anomaly = Anomaly.last
          expect(anomaly.anomaly_type).to eq("packet_loss")
          expect(anomaly.severity).to eq("warning")
        end
      end

      context "when packet loss exceeds critical threshold" do
        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: true,
            latency_ms: 10.0,
            packet_loss: 60.0  # > 50%
          )
        end

        it "creates a critical packet_loss anomaly" do
          expect {
            described_class.detect_for_measurement(measurement)
          }.to change(Anomaly, :count).by(1)

          anomaly = Anomaly.last
          expect(anomaly.anomaly_type).to eq("packet_loss")
          expect(anomaly.severity).to eq("critical")
        end
      end

      context "when packet loss returns to normal" do
        let!(:active_loss_anomaly) do
          create(:anomaly,
            site: site,
            host: baseline.host,
            anomaly_type: :packet_loss,
            severity: :warning
          )
        end

        let(:measurement) do
          create(:measurement,
            site: site,
            host: baseline.host,
            ip: baseline.ip,
            is_up: true,
            latency_ms: 10.0,
            packet_loss: 0.0
          )
        end

        it "resolves the packet_loss anomaly" do
          described_class.detect_for_measurement(measurement)

          active_loss_anomaly.reload
          expect(active_loss_anomaly.active?).to be false
        end
      end
    end
  end

  describe ".detect_for_batch" do
    let!(:baseline_record) { baseline }

    it "processes all measurements in the batch" do
      measurements = [
        create(:measurement, site: site, host: baseline.host, ip: baseline.ip, is_up: false),
        create(:measurement, site: site, host: "other-host", ip: "192.168.1.2", is_up: true, latency_ms: 10.0)
      ]

      # Only the first should create an anomaly (host_down)
      # The second has no baseline (cold start)
      expect {
        described_class.detect_for_batch(measurements)
      }.to change(Anomaly, :count).by(1)
    end
  end

  describe ".detect_for_measurement with explicit baseline parameter" do
    let(:measurement) do
      create(:measurement,
        site: site,
        host: "unknown-host",
        ip: "192.168.1.99",
        is_up: true,
        latency_ms: 10.0
      )
    end

    it "does not query for baseline when baseline: nil is explicitly passed" do
      baseline_queries = []
      callback = lambda do |_name, _start, _finish, _id, payload|
        if payload[:sql].include?("baselines") && payload[:sql].include?("SELECT")
          baseline_queries << payload[:sql]
        end
      end

      ActiveSupport::Notifications.subscribed(callback, "sql.active_record") do
        described_class.detect_for_measurement(measurement, baseline: nil)
      end

      expect(baseline_queries).to be_empty,
        "Expected no baseline queries when baseline: nil is explicit, got: #{baseline_queries.inspect}"
    end

    it "queries for baseline when baseline parameter is not provided" do
      baseline_queries = []
      callback = lambda do |_name, _start, _finish, _id, payload|
        if payload[:sql].include?("baselines") && payload[:sql].include?("SELECT")
          baseline_queries << payload[:sql]
        end
      end

      ActiveSupport::Notifications.subscribed(callback, "sql.active_record") do
        described_class.detect_for_measurement(measurement)
      end

      expect(baseline_queries.size).to eq(1),
        "Expected 1 baseline query when parameter not provided, got: #{baseline_queries.size}"
    end
  end

  describe "context snapshot" do
    let!(:baseline_record) { baseline }

    let(:measurement) do
      create(:measurement,
        site: site,
        host: baseline.host,
        ip: baseline.ip,
        is_up: false,
        latency_ms: nil
      )
    end

    it "includes measurement and baseline data" do
      described_class.detect_for_measurement(measurement)

      anomaly = Anomaly.last
      snapshot = anomaly.context_snapshot

      expect(snapshot["measurement"]).to be_present
      expect(snapshot["baseline"]).to be_present
      expect(snapshot["baseline"]["latency_p95"]).to eq(baseline.latency_p95)
    end
  end
end
