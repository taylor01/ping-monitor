require "rails_helper"

RSpec.describe BaselineCalculationService do
  describe ".calculate_stats" do
    it "calculates mean correctly" do
      latencies = [ 10.0, 20.0, 30.0, 40.0, 50.0 ]
      stats = described_class.calculate_stats(latencies)

      expect(stats[:mean]).to eq(30.0)
    end

    it "calculates standard deviation correctly" do
      latencies = [ 10.0, 20.0, 30.0, 40.0, 50.0 ]
      stats = described_class.calculate_stats(latencies)

      # stddev of [10,20,30,40,50] = sqrt(200) ≈ 14.142
      expect(stats[:stddev]).to be_within(0.01).of(14.142)
    end

    it "calculates p95 correctly" do
      latencies = (1..100).map(&:to_f)
      stats = described_class.calculate_stats(latencies)

      expect(stats[:p95]).to be_within(1).of(95)
    end

    it "calculates p99 correctly" do
      latencies = (1..100).map(&:to_f)
      stats = described_class.calculate_stats(latencies)

      expect(stats[:p99]).to be_within(1).of(99)
    end

    it "returns empty hash for empty array" do
      expect(described_class.calculate_stats([])).to eq({})
    end

    it "handles single value" do
      stats = described_class.calculate_stats([ 50.0 ])

      expect(stats[:mean]).to eq(50.0)
      expect(stats[:stddev]).to eq(0.0)
      expect(stats[:p95]).to eq(50.0)
      expect(stats[:p99]).to eq(50.0)
    end
  end

  describe ".percentile" do
    it "returns correct percentile for sorted array" do
      sorted = [ 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0 ]

      expect(described_class.percentile(sorted, 50)).to be_within(0.5).of(5.5)
      expect(described_class.percentile(sorted, 90)).to be_within(0.5).of(9.1)
    end

    it "returns the single value for single-element array" do
      expect(described_class.percentile([ 42.0 ], 95)).to eq(42.0)
    end
  end

  describe ".calculate_for_site" do
    let(:site) { create(:site) }

    context "with sufficient measurements" do
      before do
        # Create 100 measurements over the past day (more than MIN_SAMPLES)
        100.times do |i|
          create(:measurement,
            site: site,
            host: "test-host",
            ip: "192.168.1.1",
            is_up: true,
            latency_ms: 10.0 + (i % 10),  # latencies between 10-19ms
            timestamp: (100 - i).minutes.ago
          )
        end
      end

      it "creates a baseline for the host" do
        expect {
          described_class.calculate_for_site(site)
        }.to change(Baseline, :count).by(1)
      end

      it "calculates correct statistics" do
        described_class.calculate_for_site(site)

        baseline = site.baselines.find_by(host: "test-host")
        expect(baseline).to be_present
        expect(baseline.ip).to eq("192.168.1.1")
        expect(baseline.latency_mean).to be_within(1).of(14.5)
        expect(baseline.sample_count).to eq(100)
      end

      it "updates existing baseline" do
        create(:baseline, site: site, host: "test-host", ip: "192.168.1.1", sample_count: 50)

        expect {
          described_class.calculate_for_site(site)
        }.not_to change(Baseline, :count)

        baseline = site.baselines.find_by(host: "test-host")
        expect(baseline.sample_count).to eq(100)
      end
    end

    context "with insufficient measurements" do
      before do
        # Create only 30 measurements (less than MIN_SAMPLES of 60)
        30.times do |i|
          create(:measurement,
            site: site,
            host: "test-host",
            ip: "192.168.1.1",
            is_up: true,
            latency_ms: 10.0,
            timestamp: i.minutes.ago
          )
        end
      end

      it "does not create a baseline" do
        expect {
          described_class.calculate_for_site(site)
        }.not_to change(Baseline, :count)
      end
    end

    context "with only failed pings" do
      before do
        100.times do |i|
          create(:measurement,
            site: site,
            host: "test-host",
            ip: "192.168.1.1",
            is_up: false,
            latency_ms: nil,
            timestamp: i.minutes.ago
          )
        end
      end

      it "does not create a baseline" do
        expect {
          described_class.calculate_for_site(site)
        }.not_to change(Baseline, :count)
      end
    end

    context "with measurements outside window" do
      before do
        # Create measurements older than 7 days
        100.times do |i|
          create(:measurement,
            site: site,
            host: "test-host",
            ip: "192.168.1.1",
            is_up: true,
            latency_ms: 10.0,
            timestamp: 8.days.ago + i.minutes
          )
        end
      end

      it "does not create a baseline" do
        expect {
          described_class.calculate_for_site(site)
        }.not_to change(Baseline, :count)
      end
    end

    context "with multiple hosts" do
      before do
        %w[host-a host-b].each do |host|
          70.times do |i|
            create(:measurement,
              site: site,
              host: host,
              ip: "192.168.1.#{host == 'host-a' ? 1 : 2}",
              is_up: true,
              latency_ms: host == "host-a" ? 10.0 : 20.0,
              timestamp: i.minutes.ago
            )
          end
        end
      end

      it "creates baselines for each host" do
        expect {
          described_class.calculate_for_site(site)
        }.to change(Baseline, :count).by(2)
      end

      it "calculates separate statistics for each host" do
        described_class.calculate_for_site(site)

        baseline_a = site.baselines.find_by(host: "host-a")
        baseline_b = site.baselines.find_by(host: "host-b")

        expect(baseline_a.latency_mean).to eq(10.0)
        expect(baseline_b.latency_mean).to eq(20.0)
      end
    end
  end
end
