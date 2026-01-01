require "rails_helper"

RSpec.describe Anomaly, type: :model do
  describe "associations" do
    it { should belong_to(:site) }
    it { should belong_to(:measurement).optional }
    it { should have_many(:analysis_logs).dependent(:destroy) }
  end

  describe "validations" do
    it { should validate_presence_of(:anomaly_type) }
    it { should validate_presence_of(:severity) }
  end

  describe "enums" do
    it "defines anomaly_type enum" do
      expect(Anomaly.anomaly_types.keys).to contain_exactly(
        "host_down", "host_recovery", "latency_spike", "packet_loss", "site_offline"
      )
    end

    it "defines severity enum" do
      expect(Anomaly.severities.keys).to contain_exactly("info", "warning", "critical")
    end
  end

  describe "scopes" do
    let(:site) { create(:site) }

    describe ".active" do
      it "returns unresolved anomalies" do
        active = create(:anomaly, site: site)
        resolved = create(:anomaly, :resolved, site: site)

        expect(Anomaly.active).to include(active)
        expect(Anomaly.active).not_to include(resolved)
      end
    end

    describe ".resolved" do
      it "returns resolved anomalies" do
        active = create(:anomaly, site: site)
        resolved = create(:anomaly, :resolved, site: site)

        expect(Anomaly.resolved).not_to include(active)
        expect(Anomaly.resolved).to include(resolved)
      end
    end

    describe ".critical" do
      it "returns critical severity anomalies" do
        critical = create(:anomaly, :critical, site: site)
        warning = create(:anomaly, site: site, severity: :warning)

        expect(Anomaly.critical).to include(critical)
        expect(Anomaly.critical).not_to include(warning)
      end
    end

    describe ".recent" do
      it "returns anomalies created since specified time" do
        recent = create(:anomaly, site: site, created_at: 12.hours.ago)
        old = create(:anomaly, site: site, created_at: 2.days.ago)

        expect(Anomaly.recent(24.hours.ago)).to include(recent)
        expect(Anomaly.recent(24.hours.ago)).not_to include(old)
      end
    end
  end

  describe "#active?" do
    it "returns true when not resolved" do
      anomaly = build(:anomaly, resolved_at: nil)
      expect(anomaly.active?).to be true
    end

    it "returns false when resolved" do
      anomaly = build(:anomaly, resolved_at: Time.current)
      expect(anomaly.active?).to be false
    end
  end

  describe "#resolve!" do
    it "sets resolved_at to current time" do
      anomaly = create(:anomaly)
      expect(anomaly.resolved_at).to be_nil

      before_resolve = Time.current
      anomaly.resolve!

      expect(anomaly.resolved_at).to be >= before_resolve
      expect(anomaly.resolved_at).to be_within(2.seconds).of(Time.current)
    end

    it "persists the change" do
      anomaly = create(:anomaly)
      anomaly.resolve!
      anomaly.reload
      expect(anomaly.resolved_at).to be_present
    end
  end

  describe "traits" do
    describe ":critical" do
      it "creates a critical anomaly" do
        anomaly = build(:anomaly, :critical)
        expect(anomaly.severity).to eq("critical")
      end
    end

    describe ":resolved" do
      it "creates a resolved anomaly" do
        anomaly = build(:anomaly, :resolved)
        expect(anomaly.resolved_at).to be_present
        expect(anomaly.active?).to be false
      end
    end

    describe ":latency_spike" do
      it "creates a latency spike anomaly" do
        anomaly = build(:anomaly, :latency_spike)
        expect(anomaly.anomaly_type).to eq("latency_spike")
        expect(anomaly.current_value).to eq(250.0)
        expect(anomaly.baseline_value).to eq(25.0)
      end
    end
  end
end
